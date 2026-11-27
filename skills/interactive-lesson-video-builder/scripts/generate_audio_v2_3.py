import argparse
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

DIFFICULTY_SECONDS = {"D1": 6, "D2": 8, "D3": 10, "D4": 15, "D5": 20}

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError(p.stderr[-4000:])
    return p.stdout.strip()

def media_duration(ffprobe, path):
    return float(run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", str(path)]))

def compact(text):
    return re.sub(r"\s+", "", str(text or ""))

def split_phrases(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    parts = [x.strip() for x in re.split(r"(?<=[。！？；：.!?;])", text) if x.strip()]
    result, buf = [], ""
    for part in parts:
        if buf and len(buf) >= 12:
            result.append(buf)
            buf = part
        else:
            buf += part
    if buf:
        result.append(buf)
    return [x for x in result if len(x.strip()) >= 2]

def punctuation_pause_ms(text, cfg):
    if re.search(r"[？?！!]", text):
        return int(cfg.get("pause_after_question_ms", 700))
    if re.search(r"[。；;]", text):
        return int(cfg.get("pause_after_sentence_ms", 520))
    if re.search(r"[，、：:]", text):
        return int(cfg.get("pause_after_comma_ms", 260))
    return int(cfg.get("pause_after_paragraph_ms", 850))

def infer_difficulty(event):
    text = str(event.get("text", ""))
    if re.search(r"综合|设计.*方案|多种.*比较|离堂检测|综合挑战", text):
        return "D5", "prompt wording indicates synthesis or multiple constraints"
    if re.search(r"代码|递归|状态转移|懒标记|区间.*查询|逐步推导|模拟过程|证明", text):
        return "D4", "prompt requires code tracing, multi-step reasoning or algorithm simulation"
    if re.search(r"判断|区别|为什么|作用|含义|如何理解", text):
        return "D2", "prompt asks for conceptual interpretation or comparison"
    if re.search(r"是什么|定义|指出|说出|回忆", text):
        return "D1", "prompt is primarily recall or identification"
    return "D3", "default single-step reasoning level; teacher can override with difficulty"

def thinking_seconds(event, pacing):
    if event.get("thinking_seconds") is not None:
        return float(event["thinking_seconds"]), "explicit thinking_seconds"
    if event.get("pause_after_seconds") is not None:
        return float(event["pause_after_seconds"]), "legacy/explicit pause_after_seconds"
    difficulty = event.get("difficulty")
    reason = "explicit difficulty"
    if not difficulty:
        difficulty, reason = infer_difficulty(event)
    table = pacing.get("thinking_seconds_by_difficulty", DIFFICULTY_SECONDS)
    return float(table.get(str(difficulty).upper(), 10)), f"{difficulty}: {reason}"

async def synthesize(text, mp3_path, voice, rate, pitch, volume, retries):
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Install edge-tts in the active venv: python -m pip install edge-tts") from exc
    last_error = None
    for attempt in range(1, retries + 1):
        partial = mp3_path.with_suffix(".partial.mp3")
        try:
            await edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch, volume=volume).save(str(partial))
            if not partial.exists() or partial.stat().st_size < 1024:
                raise RuntimeError("TTS returned empty audio")
            partial.replace(mp3_path)
            return
        except Exception as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt < retries:
                await asyncio.sleep(min(2 ** attempt, 12))
    raise RuntimeError(f"TTS failed after {retries} attempts: {last_error}")

def ensure_wav(ffmpeg, mp3_path, wav_path):
    if wav_path.exists() and wav_path.stat().st_size > 2048:
        return
    run([ffmpeg, "-y", "-i", str(mp3_path), "-ar", "24000", "-ac", "1",
         "-c:a", "pcm_s16le", str(wav_path)])

def make_silence(ffmpeg, path, seconds):
    if not path.exists():
        run([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", f"{seconds:.3f}", "-c:a", "pcm_s16le", str(path)])

def atomic_json(path, obj):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)

async def main_async(args):
    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    voice_cfg, pacing = cfg["teacher_voice"], cfg["pacing"]
    voice = args.voice or voice_cfg["voice"]
    rate = args.rate or voice_cfg["rate"]
    pitch = args.pitch or voice_cfg["pitch"]
    volume = voice_cfg.get("volume", "+0%")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("FFmpeg and FFprobe must both be available on PATH")
    out = Path(args.output)
    timing_dir = Path(args.timings_output or (out / "timings"))
    cache = out / ".cache"
    out.mkdir(parents=True, exist_ok=True)
    timing_dir.mkdir(parents=True, exist_ok=True)
    cache.mkdir(exist_ok=True)
    if args.all_slides:
        selected = {int(s["slide"]) for s in data.get("slides", [])}
    elif args.slides:
        selected = set(args.slides)
    else:
        selected = set(pacing.get("pilot_slide_ids", [1, 20, 40, 60, 80]))
    failures, completed = [], 0

    for slide in data.get("slides", []):
        number = int(slide["slide"])
        if number not in selected:
            continue
        wav_parts, speech, pauses, difficulty_log = [], [], [], []
        cursor, char_cursor = 0.0, 0
        try:
            for index, event in enumerate(slide.get("events", []), 1):
                kind = event.get("type", "narration")
                event_id = event.get("event_id", f"s{number:03d}_e{index:02d}")
                if kind == "pause":
                    seconds = float(event.get("duration_seconds", event.get("pause_after_seconds", 0)) or 0)
                    if seconds > 0:
                        silence = cache / f"silence_{int(seconds*1000)}.wav"
                        make_silence(ffmpeg, silence, seconds)
                        measured = media_duration(ffprobe, silence)
                        wav_parts.append(silence)
                        pauses.append({"event_id": event_id, "kind": "explicit", "start": round(cursor,3),
                                       "end": round(cursor+measured,3), "duration_seconds": round(measured,3)})
                        cursor += measured
                    continue
                if kind not in ("narration", "thinking_prompt", "reveal", "summary"):
                    raise ValueError(f"Unsupported event type: {kind}")
                phrases = split_phrases(event.get("text", ""))
                for phrase_index, phrase in enumerate(phrases):
                    key = hashlib.sha256("\n".join([phrase, voice, rate, pitch, volume]).encode("utf-8")).hexdigest()
                    mp3, wav = cache / f"{key}.mp3", cache / f"{key}.wav"
                    if not mp3.exists():
                        await synthesize(phrase, mp3, voice, rate, pitch, volume, args.retries)
                    ensure_wav(ffmpeg, mp3, wav)
                    measured = media_duration(ffprobe, wav)
                    speech.append({"event_id": event_id, "type": kind, "text": phrase,
                                   "start": round(cursor,3), "end": round(cursor+measured,3),
                                   "source_char_start": char_cursor,
                                   "source_char_end": char_cursor+len(compact(phrase)),
                                   "pause_after_seconds": 0})
                    wav_parts.append(wav)
                    cursor += measured
                    char_cursor += len(compact(phrase))
                    if phrase_index < len(phrases)-1:
                        ms = punctuation_pause_ms(phrase, voice_cfg)
                        silence = cache / f"natural_{ms}.wav"
                        make_silence(ffmpeg, silence, ms/1000)
                        d = media_duration(ffprobe, silence)
                        wav_parts.append(silence)
                        pauses.append({"event_id": event_id, "kind": "natural", "start": round(cursor,3),
                                       "end": round(cursor+d,3), "duration_seconds": round(d,3)})
                        cursor += d

                if kind == "thinking_prompt":
                    seconds, rationale = thinking_seconds(event, pacing)
                    difficulty_log.append({"event_id": event_id, "seconds": seconds, "rationale": rationale})
                    pause_kind = "thinking_prompt"
                elif event.get("knowledge_point_end"):
                    seconds = float(event.get("pause_after_seconds", pacing.get("knowledge_point_pause_seconds", 5)))
                    pause_kind = "knowledge_point"
                else:
                    seconds = float(event.get("pause_after_seconds", 0) or 0)
                    pause_kind = "explicit"
                if seconds > 0:
                    silence = cache / f"event_pause_{int(seconds*1000)}.wav"
                    make_silence(ffmpeg, silence, seconds)
                    d = media_duration(ffprobe, silence)
                    wav_parts.append(silence)
                    pauses.append({"event_id": event_id, "kind": pause_kind, "start": round(cursor,3),
                                   "end": round(cursor+d,3), "duration_seconds": round(d,3)})
                    if speech and speech[-1]["event_id"] == event_id:
                        speech[-1]["pause_after_seconds"] = round(d,3)
                    cursor += d

            end_pause = float(slide.get("slide_end_pause_seconds", pacing.get("slide_end_pause_seconds", 5)))
            if end_pause > 0:
                silence = cache / f"slide_end_{int(end_pause*1000)}.wav"
                make_silence(ffmpeg, silence, end_pause)
                d = media_duration(ffprobe, silence)
                wav_parts.append(silence)
                pauses.append({"event_id": None, "kind": "slide_end", "start": round(cursor,3),
                               "end": round(cursor+d,3), "duration_seconds": round(d,3)})
                cursor += d
            if not wav_parts:
                raise RuntimeError("No speech or pause segments found")
            concat = cache / f"concat_{number:03d}.txt"
            concat.write_text("\n".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'" for p in wav_parts) + "\n", encoding="utf-8")
            tmp_wav = out / f"slide_{number:03d}.building.wav"
            run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "pcm_s16le", str(tmp_wav)])
            destination = out / f"slide_{number:03d}.mp3"
            run([ffmpeg, "-y", "-i", str(tmp_wav), "-codec:a", "libmp3lame", "-q:a", "3", str(destination)])
            tmp_wav.unlink(missing_ok=True)
            actual_duration = media_duration(ffprobe, destination)
            timing = {"schema_version":"2.3.0", "slide":number, "duration_seconds":round(actual_duration,3),
                      "alignment_mode":"measured_phrase_boundaries", "speech_events":speech, "pauses":pauses,
                      "thinking_difficulty":difficulty_log,
                      "limitations":["Phrase-level measured timing; not word- or phoneme-level forced alignment."]}
            atomic_json(timing_dir / f"slide_{number:03d}.json", timing)
            completed += 1
            print(f"Slide {number}: {actual_duration:.2f}s; {len(speech)} phrases; {len(pauses)} pauses")
        except Exception as exc:
            failures.append((number, str(exc)))
            print(f"FAILED slide {number}: {exc}")
    print(f"V2.3 audio: {completed} completed, {len(failures)} failed")
    if failures:
        for n, message in failures:
            print(f"  slide {n}: {message}")
        raise SystemExit(2)

def main():
    p=argparse.ArgumentParser(description="V2.3 event-driven TTS and measured phrase timings")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--timings-output"); p.add_argument("--config", default="config/video_ux_v2_3.json")
    p.add_argument("--slides", nargs="*", type=int); p.add_argument("--all-slides", action="store_true")
    p.add_argument("--voice"); p.add_argument("--rate"); p.add_argument("--pitch"); p.add_argument("--retries", type=int, default=4)
    asyncio.run(main_async(p.parse_args()))
if __name__ == "__main__":
    main()
