"""End-to-end media QA for V2.4 rendered lesson videos."""
import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(command):
    process = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if process.returncode:
        raise RuntimeError(process.stderr[-5000:])
    return process.stdout.strip()


def parse_srt_time(value):
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", value.strip())
    require(match is not None, f"Invalid SRT timestamp: {value}")
    hours, minutes, seconds, millis = map(int, match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def read_srt(path):
    content = Path(path).read_text(encoding="utf-8-sig")
    if not content.strip():
        return []
    blocks = re.split(r"\r?\n\s*\r?\n", content.strip())
    cues = []
    for block in blocks:
        lines = [line.rstrip("\r") for line in block.splitlines()]
        require(len(lines) >= 3, "Malformed SRT cue block")
        require(lines[0].strip().isdigit(), "SRT cue index must be numeric")
        times = re.fullmatch(r"(.+?)\s+-->\s+(.+)", lines[1].strip())
        require(times is not None, "Malformed SRT time range")
        start, end = parse_srt_time(times.group(1)), parse_srt_time(times.group(2))
        text = "\n".join(lines[2:]).strip()
        require(0 <= start < end and bool(text), "Empty or invalid SRT cue")
        if cues:
            require(start >= cues[-1][1] - 0.003, "SRT cues overlap or are out of order")
        cues.append((start, end, text))
    return cues


def validate_focus_report(report):
    require(
        report.get("version") in ("2.4.0-alpha.3", "2.4.1-alpha.4"),
        "Unexpected V2.4 QA report version",
    )
    require(report.get("manual_review_required") is True, "Manual review must remain required")
    require(report.get("auto_approved") is False, "V2.4 must never auto-approve a full course")
    slides = report.get("slides")
    require(isinstance(slides, list) and slides, "QA report has no slide rows")
    slide_ids = [int(row["slide"]) for row in slides]
    require(len(slide_ids) == len(set(slide_ids)), "Duplicate slide ID in QA report")
    require(slide_ids == sorted(slide_ids), "Slide rows must be in ascending order")
    require(int(report.get("slide_count", -1)) == len(slides), "Slide count does not match rows")

    total = 0.0
    merged_total = 0
    cue_total = 0
    for row in slides:
        page = int(row["slide"])
        duration = float(row["duration_seconds"])
        require(math.isfinite(duration) and duration > 0, f"Slide {page}: invalid duration")
        total += duration
        cue_total += int(row.get("subtitle_cues", 0))
        require(int(row.get("subtitle_cues", 0)) >= 0, f"Slide {page}: invalid subtitle count")

        regions = row.get("focus_alignment", [])
        require(isinstance(regions, list), f"Slide {page}: focus_alignment must be a list")
        phrase_map = {}
        unique_focus_intervals = []
        merged_here = 0
        for region_index, region in enumerate(regions):
            region_id = str(region.get("region_id", region_index))
            intervals = region.get("intervals", [])
            require(isinstance(intervals, list), f"Slide {page}: region intervals must be a list")
            if region.get("reason") == "merged_duplicate_geometry":
                merged_here += 1
                require(not intervals, f"Slide {page}: merged duplicate region must not draw again")
                owner = int(region.get("merged_into_region_index", -1))
                require(0 <= owner < region_index, f"Slide {page}: invalid merged region owner")
            for interval in intervals:
                start, end = float(interval["start"]), float(interval["end"])
                event_id = str(interval.get("event_id", ""))
                phrase_text = str(interval.get("phrase_text", interval.get("phrase", "")))
                require(
                    math.isfinite(start)
                    and math.isfinite(end)
                    and 0 <= start < end <= duration + 0.05,
                    f"Slide {page}: focus interval outside slide duration",
                )
                require(bool(event_id), f"Slide {page}: focus interval missing event ID")
                if interval.get("phrase_index") is not None:
                    phrase_key = (event_id, int(interval["phrase_index"]))
                else:
                    phrase_key = (event_id, phrase_text, round(start, 4), round(end, 4))
                existing = phrase_map.get(phrase_key)
                if existing is None:
                    phrase_map[phrase_key] = {
                        "start": start, "end": end, "phrase_text": phrase_text,
                        "regions": {region_id},
                    }
                    unique_focus_intervals.append((start, end, phrase_key))
                else:
                    require(
                        abs(existing["start"] - start) <= 0.003
                        and abs(existing["end"] - end) <= 0.003
                        and existing["phrase_text"] == phrase_text,
                        f"Slide {page}: one phrase has conflicting focus intervals",
                    )
                    require(
                        region_id not in existing["regions"],
                        f"Slide {page}: duplicate phrase focus within the same region",
                    )
                    existing["regions"].add(region_id)

        unique_focus_intervals.sort(key=lambda item: (item[0], item[1]))
        for previous, current in zip(unique_focus_intervals, unique_focus_intervals[1:]):
            require(
                current[0] >= previous[1] - 0.003,
                f"Slide {page}: distinct spoken phrases have overlapping focus intervals",
            )
        require(
            int(row.get("merged_duplicate_focus_regions", 0)) == merged_here,
            f"Slide {page}: duplicate-geometry count mismatch",
        )
        merged_total += merged_here

    recorded_total = float(report.get("total_duration_seconds", -1))
    require(
        math.isfinite(recorded_total)
        and abs(recorded_total - total) <= max(0.05, 0.01 * len(slides)),
        "QA report total duration does not match its slide rows",
    )
    return {
        "slides": slides,
        "slide_ids": slide_ids,
        "slide_duration_sum": total,
        "subtitle_cues": cue_total,
        "merged_duplicate_focus_regions": merged_total,
    }

def validate_timing_record(page, timing, audio_duration, cues, expected_cues):
    require(int(timing["slide"]) == page, f"Slide {page}: timing file ID mismatch")
    recorded_duration = float(timing["duration_seconds"])
    require(
        math.isfinite(recorded_duration) and abs(recorded_duration - audio_duration) <= 0.15,
        f"Slide {page}: timing/audio duration mismatch",
    )

    speech = timing.get("speech_events", [])
    pauses = timing.get("pauses", [])
    require(speech, f"Slide {page}: no speech timing events")
    intervals = []
    for event in speech:
        start, end = float(event["start"]), float(event["end"])
        require(
            math.isfinite(start)
            and math.isfinite(end)
            and 0 <= start < end <= audio_duration + 0.05,
            f"Slide {page}: invalid speech interval",
        )
        intervals.append((start, end, "speech"))
    thinking = []
    for pause in pauses:
        start, end = float(pause["start"]), float(pause["end"])
        require(
            math.isfinite(start)
            and math.isfinite(end)
            and 0 <= start < end <= audio_duration + 0.05,
            f"Slide {page}: invalid pause interval",
        )
        intervals.append((start, end, "pause"))
        if pause.get("kind") == "thinking_prompt":
            thinking.append((start, end))

    intervals.sort(key=lambda item: (item[0], item[1]))
    last_end = 0.0
    for start, end, _kind in intervals:
        require(start >= last_end - 0.003, f"Slide {page}: speech/pause intervals overlap")
        require(start <= last_end + 0.15, f"Slide {page}: unexplained timing gap")
        last_end = end
    require(abs(last_end - audio_duration) <= 0.20, f"Slide {page}: timing does not cover audio")

    require(len(cues) == expected_cues, f"Slide {page}: SRT cue count differs from QA report")
    for start, end, text in cues:
        require(end <= audio_duration + 0.10, f"Slide {page}: SRT cue exceeds audio duration")
        require(
            any(start >= a - 0.003 and end <= b + 0.003 for a, b, _ in intervals if _ == "speech"),
            f"Slide {page}: subtitle lies outside a speech interval",
        )
        require(
            not any(min(end, pause_end) - max(start, pause_start) > 0.003
                    for pause_start, pause_end in thinking),
            f"Slide {page}: subtitle overlaps a thinking pause",
        )
    return {
        "slide": page,
        "audio_duration_seconds": round(audio_duration, 3),
        "speech_events": len(speech),
        "pauses": len(pauses),
        "subtitle_cues": len(cues),
    }


def probe_duration(ffprobe, path):
    raw = run(
        [
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path),
        ]
    )
    duration = float(raw)
    require(math.isfinite(duration) and duration > 0, f"Invalid media duration: {path}")
    return duration


def probe_video(ffprobe, path):
    data = json.loads(
        run(
            [
                ffprobe, "-v", "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height,avg_frame_rate,duration",
                "-of", "json", str(path),
            ]
        )
    )
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    require(video is not None and audio is not None, "Final video must contain video and audio streams")
    duration = float(data["format"]["duration"])
    video_duration = float(video.get("duration", duration))
    audio_duration = float(audio.get("duration", duration))
    require(all(math.isfinite(x) and x > 0 for x in (duration, video_duration, audio_duration)),
            "Invalid final video stream duration")
    return {
        "duration": duration,
        "video_duration": video_duration,
        "audio_duration": audio_duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": video.get("avg_frame_rate"),
    }


def validate_video(video, report, audio_dir, timings_dir, subtitle_dir, ffprobe, ffmpeg, decode=True):
    summary = validate_focus_report(report)
    media = probe_video(ffprobe, video)
    expected_resolution = report.get("resolution", "")
    match = re.fullmatch(r"(\d+)x(\d+)", expected_resolution)
    require(match is not None, "QA report resolution must use WIDTHxHEIGHT")
    require(
        (media["width"], media["height"]) == (int(match.group(1)), int(match.group(2))),
        "Final video resolution differs from renderer QA report",
    )
    tolerance = max(0.5, 0.04 * len(summary["slides"]))
    require(
        abs(media["duration"] - summary["slide_duration_sum"]) <= tolerance,
        "Final video duration differs from sum of slide durations",
    )
    require(
        abs(media["video_duration"] - media["audio_duration"]) <= max(0.35, 0.01 * media["duration"]),
        "Final video and audio stream durations differ",
    )

    audio_dir, timings_dir, subtitle_dir = map(Path, (audio_dir, timings_dir, subtitle_dir))
    per_slide = []
    for row in summary["slides"]:
        page = int(row["slide"])
        audio = audio_dir / f"slide_{page:03d}.mp3"
        timing_path = timings_dir / f"slide_{page:03d}.json"
        subtitle_path = subtitle_dir / f"slide_{page:03d}.srt"
        require(audio.exists(), f"Slide {page}: missing audio file {audio}")
        require(timing_path.exists(), f"Slide {page}: missing timing file {timing_path}")
        require(subtitle_path.exists(), f"Slide {page}: missing subtitle file {subtitle_path}")
        audio_duration = probe_duration(ffprobe, audio)
        timing = json.loads(timing_path.read_text(encoding="utf-8-sig"))
        cues = read_srt(subtitle_path)
        per_slide.append(
            validate_timing_record(page, timing, audio_duration, cues, int(row["subtitle_cues"]))
        )

    if decode:
        run(
            [
                ffmpeg, "-v", "error", "-xerror", "-i", str(video),
                "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-",
            ]
        )

    return {
        "version": "2.4.0-alpha.3",
        "passed": True,
        "manual_review_required": True,
        "auto_approved": False,
        "video": str(video),
        "video_duration_seconds": round(media["duration"], 3),
        "video_stream_duration_seconds": round(media["video_duration"], 3),
        "audio_stream_duration_seconds": round(media["audio_duration"], 3),
        "resolution": f"{media['width']}x{media['height']}",
        "fps": media["fps"],
        "slide_count": len(per_slide),
        "subtitle_cues": sum(row["subtitle_cues"] for row in per_slide),
        "merged_duplicate_focus_regions": summary["merged_duplicate_focus_regions"],
        "decoded_entire_video": bool(decode),
        "slides": per_slide,
        "limitations": [
            "Phrase-level timing checks do not prove word-level alignment or semantic subtitle accuracy.",
            "Video decode and stream checks do not prove visual legibility or teaching correctness.",
            "Manual frame-level review of focus placement, subtitle overlap, and narration pacing remains mandatory.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--qa-report", required=True)
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--timings-dir", required=True)
    parser.add_argument("--subtitle-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ffprobe", default=shutil.which("ffprobe"))
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--skip-decode", action="store_true")
    args = parser.parse_args()

    require(args.ffprobe, "FFprobe must be available on PATH")
    if not args.skip_decode:
        require(args.ffmpeg, "FFmpeg must be available on PATH unless --skip-decode is used")

    report = json.loads(Path(args.qa_report).read_text(encoding="utf-8-sig"))
    result = validate_video(
        args.video,
        report,
        args.audio_dir,
        args.timings_dir,
        args.subtitle_dir,
        args.ffprobe,
        args.ffmpeg or "",
        decode=not args.skip_decode,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
