"""Render V2.4.1 compiled visual/speech/timeline alignment reports."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(command):
    process = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if process.returncode:
        raise RuntimeError(process.stderr[-5000:])
    return process.stdout.strip()


def probe_duration(ffprobe, path):
    return float(run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ]))


def image_size(ffprobe, path):
    data = json.loads(run([
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(path)
    ]))
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def srt_time(seconds):
    ms = max(0, int(round(seconds * 1000)))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def escpath(path):
    return str(Path(path).resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def thinking_intervals(timing):
    return [
        (float(row["start"]), float(row["end"]))
        for row in timing.get("pauses", [])
        if row.get("kind") == "thinking_prompt" and float(row["end"]) > float(row["start"])
    ]


def subtract_intervals(start, end, intervals):
    pieces = [(start, end)]
    for a, b in intervals:
        next_pieces = []
        for x, y in pieces:
            if b <= x or a >= y:
                next_pieces.append((x, y))
            else:
                if x < a:
                    next_pieces.append((x, a))
                if b < y:
                    next_pieces.append((b, y))
        pieces = next_pieces
    return [(x, y) for x, y in pieces if y - x >= 0.08]


def wrap_caption(text, width, max_lines):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    lines, current = [], ""
    for token in re.split(r"(\s+)", text):
        if not token:
            continue
        if token.isspace():
            if current and len(current) + len(token) <= width:
                current += token
            continue
        while len(token) > width:
            available = width - len(current)
            if available > 0:
                current += token[:available]
                token = token[available:]
                lines.append(current.rstrip())
                current = ""
            else:
                lines.append(current.rstrip())
                current = ""
        if len(current) + len(token) <= width:
            current += token
        else:
            if current:
                lines.append(current.rstrip())
            current = token
    if current:
        lines.append(current.rstrip())
    return [
        "\n".join(lines[index:index + max_lines])
        for index in range(0, len(lines), max_lines)
    ]


def make_srt(timing, path, config):
    cues = []
    hidden = thinking_intervals(timing) if config.get("disable_during_thinking", True) else []
    width = int(config.get("max_chars_per_line", 16))
    max_lines = int(config.get("max_lines", 2))
    for event in timing.get("speech_events", []):
        text = re.sub(r"\s+", " ", str(event.get("text", ""))).strip()
        start, end = float(event["start"]), float(event["end"])
        if not text or end <= start:
            continue
        blocks = wrap_caption(text, width, max_lines)
        weights = [max(1, len(block.replace("\n", ""))) for block in blocks]
        total_weight = sum(weights)
        cursor = start
        used = 0
        for block, weight in zip(blocks, weights):
            next_time = end if used + weight >= total_weight else start + (end - start) * (used + weight) / total_weight
            visible = subtract_intervals(cursor, next_time, hidden) if hidden else [(cursor, next_time)]
            for visible_start, visible_end in visible:
                cues.append((visible_start, visible_end, block))
            cursor = next_time
            used += weight
    lines = []
    for index, (start, end, caption) in enumerate(cues, 1):
        lines.extend([str(index), f"{srt_time(start)} --> {srt_time(end)}", caption, ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8-sig")
    return cues


def validate_alignment_report(report):
    if report.get("schema_version") != "2.4.1":
        raise ValueError("Unsupported compiled alignment schema")
    if report.get("auto_approved") is not False or report.get("manual_review_required") is not True:
        raise ValueError("Compiled alignment must retain manual review gate")
    slides = report.get("slides", [])
    if not slides:
        raise ValueError("Compiled alignment contains no slides")
    ids = [int(row["slide"]) for row in slides]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("Compiled alignment slide IDs must be unique and ordered")
    return {int(row["slide"]): row for row in slides}



def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_render_inputs(slide_map, slides_dir, audio_dir, timings_dir,
                           source_fingerprints, selected_slides=None):
    """Fail closed if any render input differs from the compiler's audited source."""
    if not isinstance(source_fingerprints, dict):
        raise ValueError("Compiled report is missing source_fingerprints")
    timing_hashes = source_fingerprints.get("timing_sha256")
    audio_hashes = source_fingerprints.get("audio_sha256")
    if not isinstance(timing_hashes, dict) or not isinstance(audio_hashes, dict):
        raise ValueError("Compiled report is missing timing/audio fingerprints")
    pages = sorted(set(selected_slides) if selected_slides else slide_map)
    if not pages:
        raise ValueError("No slides selected for source-integrity validation")
    for page in pages:
        if page not in slide_map:
            raise ValueError(f"Slide {page}: absent from compiled alignment")
        image = Path(slides_dir) / f"slide_{page:03d}.png"
        audio = Path(audio_dir) / f"slide_{page:03d}.mp3"
        timing = Path(timings_dir) / f"slide_{page:03d}.json"
        for path in (image, audio, timing):
            if not path.is_file():
                raise FileNotFoundError(f"Slide {page}: required render input missing: {path}")
        expected_image = slide_map[page].get("slide_image_sha256")
        expected_audio = audio_hashes.get(str(page))
        expected_timing = timing_hashes.get(str(page))
        if not expected_image or not expected_audio or not expected_timing:
            raise ValueError(f"Slide {page}: compiled report lacks one or more source fingerprints")
        actual = {
            "slide image": (sha256_file(image), expected_image),
            "audio": (sha256_file(audio), expected_audio),
            "timing JSON": (sha256_file(timing), expected_timing),
        }
        for label, (observed, expected) in actual.items():
            if observed != expected:
                raise ValueError(f"Slide {page}: {label} fingerprint mismatch; refusing stale/mixed-source render")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slides", required=True, help="Directory of rendered slide PNGs")
    parser.add_argument("--audio", required=True, help="Directory of per-slide MP3 files")
    parser.add_argument("--speech-timings", required=True)
    parser.add_argument("--alignment-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--qa", default="qa_v2_4")
    parser.add_argument("--ux-config", default="config/video_ux_v2_4.json")
    parser.add_argument("--subtitle-dir", default="subtitles_v2_4")
    parser.add_argument("--only-slides", nargs="*", type=int)
    parser.add_argument("--font-file", default=r"C:\Windows\Fonts\msyh.ttc")
    args = parser.parse_args()

    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("FFmpeg and FFprobe must be available on PATH")
    config = json.loads(Path(args.ux_config).read_text(encoding="utf-8-sig"))
    alignment_report = json.loads(Path(args.alignment_report).read_text(encoding="utf-8-sig"))
    slide_map = validate_alignment_report(alignment_report)
    selected = set(args.only_slides or [])
    if selected and not selected <= set(slide_map):
        raise SystemExit("Requested slide is absent from compiled alignment")

    width = int(config["resolution"]["width"])
    height = int(config["resolution"]["height"])
    fps = int(config["resolution"]["fps"])
    band = int(config["layout"]["subtitle_band_height"])
    content_height = height - band
    slides_dir, audio_dir = Path(args.slides), Path(args.audio)
    timings_dir = Path(args.speech_timings)
    validate_render_inputs(
        slide_map, slides_dir, audio_dir, timings_dir,
        alignment_report.get("source_fingerprints"), selected or None,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    qa_dir = Path(args.qa)
    qa_dir.mkdir(parents=True, exist_ok=True)
    subtitle_dir = Path(args.subtitle_dir)
    subtitle_dir.mkdir(parents=True, exist_ok=True)

    rendered_rows, clips = [], []
    with tempfile.TemporaryDirectory(prefix="lesson_v24a4_") as temporary:
        temporary = Path(temporary)
        concat_file = output.parent / f"{output.stem}_concat.txt"
        for page in sorted(slide_map):
            if selected and page not in selected:
                continue
            row = slide_map[page]
            image = slides_dir / f"slide_{page:03d}.png"
            audio = audio_dir / f"slide_{page:03d}.mp3"
            timing_path = timings_dir / f"slide_{page:03d}.json"
            if not all(path.is_file() for path in (image, audio, timing_path)):
                raise SystemExit(f"Slide {page}: missing image/audio/timing input")
            timing = json.loads(timing_path.read_text(encoding="utf-8-sig"))
            duration = probe_duration(ffprobe, audio)
            if abs(float(row["duration_seconds"]) - duration) > 0.15:
                raise SystemExit(f"Slide {page}: audio duration differs from compiled alignment")
            srt = subtitle_dir / f"slide_{page:03d}.srt"
            cues = make_srt(timing, srt, config["subtitle"])

            image_width, image_height = image_size(ffprobe, image)
            scale = min(width / image_width, content_height / image_height)
            scaled_width, scaled_height = image_width * scale, image_height * scale
            offset_x = (width - scaled_width) / 2
            offset_y = (content_height - scaled_height) / 2
            filters = [
                f"scale={width}:{content_height}:force_original_aspect_ratio=decrease",
                f"pad={width}:{content_height}:(ow-iw)/2:(oh-ih)/2:color=black",
                f"pad={width}:{height}:0:0:color={config['layout']['subtitle_band_color']}",
            ]
            focus = config["focus"]
            colors = {
                "knowledge": focus["knowledge_color"],
                "code": focus["code_color"],
                "algorithm": focus["algorithm_color"],
            }
            focus_rows = []
            matched_count = 0
            for region_index, region in enumerate(row.get("regions", [])):
                bbox = region["bbox"]
                x, y, box_width, box_height = [float(value) for value in bbox]
                px = max(0, min(width - 2, round(offset_x + x * scaled_width)))
                py = max(0, min(content_height - 2, round(offset_y + y * scaled_height)))
                pw = max(2, min(width - px, round(box_width * scaled_width)))
                ph = max(2, min(content_height - py, round(box_height * scaled_height)))
                color = colors.get(region.get("kind"), colors["knowledge"])
                intervals = region.get("intervals", [])
                for interval in intervals:
                    start, end = float(interval["start"]), float(interval["end"])
                    enable = f"gte(t,{start:.3f})*lt(t,{end:.3f})"
                    filters.append(
                        f"drawbox=x={px}:y={py}:w={pw}:h={ph}:color={color}:t=fill:enable='{enable}'"
                    )
                    filters.append(
                        f"drawbox=x={px}:y={py}:w={pw}:h={ph}:color={focus['border_color']}:t={int(focus['border_width'])}:enable='{enable}'"
                    )
                if intervals:
                    matched_count += 1
                focus_rows.append({
                    "region_index": region_index,
                    "region_id": region["region_id"],
                    "intervals": intervals,
                    "reason": "matched" if intervals else "no_verified_phrase_mapping",
                })
                for alias in region.get("aliases", []):
                    focus_rows.append({
                        "region_index": len(focus_rows),
                        "region_id": alias,
                        "intervals": [],
                        "reason": "merged_duplicate_geometry",
                        "merged_into_region_index": region_index,
                    })

            thinking = thinking_intervals(timing)
            countdown = config["countdown"]
            font = Path(args.font_file)
            if not font.exists():
                font = Path(countdown.get("font_file", ""))
            font_option = f"fontfile='{escpath(font)}':" if font.exists() else ""
            if countdown.get("enabled", True):
                for start, end in thinking:
                    expression = f"ceil({end:.3f}-t)"
                    x = f"w-text_w-{int(config['layout'].get('countdown_right_margin', 52))}"
                    y = f"h-text_h-{int(config['layout'].get('countdown_bottom_margin', 27))}"
                    filters.append(
                        f"drawtext={font_option}text='%{{eif\\:{expression}\\:d}}':"
                        f"fontcolor={countdown['font_color']}:fontsize={int(countdown['font_size'])}:"
                        f"x={x}:y={y}:enable='between(t,{start:.3f},{end:.3f})'"
                    )
            subtitle = config["subtitle"]
            if subtitle.get("enabled", True):
                style = (
                    f"FontName={subtitle['font_name']},FontSize={int(subtitle['font_size'])},"
                    f"PrimaryColour={subtitle['color']},OutlineColour=&H80000000,BorderStyle=1,"
                    f"Outline={int(subtitle['outline'])},Shadow={int(subtitle['shadow'])},"
                    f"Alignment=2,MarginV={int(subtitle['margin_vertical'])},"
                    f"MarginR={int(subtitle.get('margin_right', 190))}"
                )
                filters.append(f"subtitles='{escpath(srt)}':force_style='{style}'")

            clip = temporary / f"slide_{page:03d}.mp4"
            run([
                ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
                "-t", f"{duration:.3f}", "-vf", ",".join(filters), "-r", str(fps),
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", str(clip),
            ])
            clips.append(clip)
            rendered_rows.append({
                "slide": page,
                "duration_seconds": round(duration, 3),
                "subtitle_cues": len(cues),
                "thinking_intervals": len(thinking),
                "thinking_seconds": round(sum(end - start for start, end in thinking), 3),
                "matched_focus_regions": matched_count,
                "unmatched_focus_regions": sum(1 for x in focus_rows if not x["intervals"] and x.get("reason") != "merged_duplicate_geometry"),
                "merged_duplicate_focus_regions": sum(1 for x in focus_rows if x.get("reason") == "merged_duplicate_geometry"),
                "unmatched_phrases": len(row.get("unmatched_phrases", [])),
                "review_required_phrases": len(row.get("review_required_phrases", [])),
                "coordinate_transform": {
                    "scale": round(scale, 7),
                    "offset_x": round(offset_x, 3),
                    "offset_y": round(offset_y, 3),
                },
                "focus_alignment": focus_rows,
            })
            print(
                f"Rendered slide {page}: {duration:.2f}s, {len(cues)} subtitle cues, "
                f"{matched_count} focus regions"
            )

        if not clips:
            raise SystemExit("No slides selected")
        concat_file.write_text(
            "\n".join(
                "file '" + clip.resolve().as_posix().replace("'", "'\\''") + "'"
                for clip in clips
            ) + "\n",
            encoding="utf-8",
        )
        run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)])

    metadata = json.loads(run([
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate", "-of", "json", str(output)
    ]))["streams"][0]
    qa_report = {
        "version": "2.4.1-alpha.4",
        "slide_count": len(rendered_rows),
        "total_duration_seconds": round(sum(row["duration_seconds"] for row in rendered_rows), 3),
        "resolution": f"{metadata['width']}x{metadata['height']}",
        "fps": metadata.get("avg_frame_rate"),
        "subtitle_alignment": "phrase-level measured timestamps, not word/phoneme forced alignment",
        "alignment_report_version": alignment_report["version"],
        "matched_phrase_count": alignment_report["matched_phrase_count"],
        "review_required_phrase_count": alignment_report["review_required_phrase_count"],
        "unmatched_phrase_count": alignment_report["unmatched_phrase_count"],
        "auto_approved": False,
        "manual_review_required": True,
        "slides": rendered_rows,
        "limitations": [
            "The semantic association is AI-proposed and second-pass verified; deterministic validation checks source identity, evidence, geometry, and time.",
            "Phrase-level alignment is not word-level or phoneme-level forced alignment.",
            "Frame-level visual quality and instructional correctness still require human review.",
        ],
    }
    report_path = qa_dir / "qa_report_v2_4_alpha4.json"
    report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Video: {output}")
    print(f"QA: {report_path}")


if __name__ == "__main__":
    main()
