"""Bind replay-validated DSU frames to measured narration phrases.

This standalone compiler verifies structural correspondence, not semantic
correctness of the original lesson. No guessed sub-phrase timestamps.
"""
import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path

from dsu_trace_v29 import validate_trace
from render_dsu_frames_v29 import render_trace


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compile_timeline(trace, frames_dir, timing, bindings):
    validate_trace(trace)
    frames_dir = Path(frames_dir)
    manifest = json.loads((frames_dir / "frames.json").read_text(encoding="utf-8"))
    # Regenerate expected images, not merely trust hashes from the same manifest.
    with tempfile.TemporaryDirectory() as tmp:
        expected = render_trace(trace, Path(tmp) / "expected")
    if manifest != expected:
        raise ValueError("Frame manifest differs from deterministic replay")
    for frame in manifest["frames"]:
        if hashlib.sha256((frames_dir / frame["file"]).read_bytes()).hexdigest() != frame["sha256"]:
            raise ValueError("Frame fingerprint mismatch")
    if timing.get("schema_version") != "2.4.1":
        raise ValueError("Unsupported measured timing schema")
    if bindings.get("trace_sha256") != digest(trace) or bindings.get("timing_sha256") != digest(timing):
        raise ValueError("Binding fingerprint mismatch")
    if bindings.get("slide") != timing.get("slide"):
        raise ValueError("Binding slide mismatch")
    duration = float(timing["duration_seconds"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid duration")
    speech = {}
    last_end = 0.0
    for event in timing["speech_events"]:
        key = (event["event_id"], event["phrase_index"])
        start, end = float(event["start"]), float(event["end"])
        if key in speech or not (math.isfinite(start) and math.isfinite(end) and last_end <= start < end <= duration):
            raise ValueError("Invalid or unordered speech interval")
        speech[key] = event
        last_end = end
    pauses = []
    for pause in timing.get("pauses", []):
        start, end = float(pause["start"]), float(pause["end"])
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration):
            raise ValueError("Invalid pause")
        pauses.append((start, end))
    rows = []
    previous_frame = -1
    previous_end = 0.0
    used = set()
    for binding in bindings["bindings"]:
        frame_index = binding["frame_index"]
        if type(frame_index) is not int or frame_index != previous_frame + 1 or frame_index >= len(manifest["frames"]):
            raise ValueError("Frames must occur once in complete replay order")
        key = (binding["event_id"], binding["phrase_index"])
        if key not in speech or key in used:
            raise ValueError("Missing or duplicate speech phrase")
        event = speech[key]
        if binding.get("phrase_text") != event["text"]:
            raise ValueError("Stale phrase text")
        start, end = float(event["start"]), float(event["end"])
        if start < previous_end or any(start < b and end > a for a,b in pauses):
            raise ValueError("Overlapping or pause-crossing binding")
        if event.get("type") == "thinking_prompt":
            raise ValueError("Thinking prompt cannot trigger a state change")
        frame = manifest["frames"][frame_index]
        rows.append({"frame_index": frame_index, "step_index": frame["step_index"],
                     "file": frame["file"], "sha256": frame["sha256"],
                     "event_id": key[0], "phrase_index": key[1],
                     "start": start, "end": end})
        used.add(key)
        previous_frame, previous_end = frame_index, end
    if len(rows) != len(manifest["frames"]):
        raise ValueError("Incomplete frame coverage")
    return {"schema_version":"2.9.1", "slide": timing["slide"],
            "trace_sha256": digest(trace), "timing_sha256": digest(timing),
            "duration_seconds": duration, "intervals": rows,
            "gap_policy": "original_slide", "source_verified": False,
            "speech_timing_bound": True, "semantic_review_required": True,
            "auto_approved": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("trace", "frames_dir", "timing", "bindings", "output"):
        parser.add_argument(name)
    args = parser.parse_args()
    def load(path):
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    result = compile_timeline(load(args.trace), args.frames_dir, load(args.timing), load(args.bindings))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
