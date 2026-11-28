"""Render a replay-validated DSU timeline as a standalone narrated MP4.

Requires FFmpeg with librsvg decoding. This is not source-semantic approval.
"""
import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compile_dsu_timeline_v29 import compile_timeline


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def frame_schedule(timeline, fps):
    if type(fps) is not int or not 1 <= fps <= 60:
        raise ValueError("Invalid fps")
    total = math.ceil(timeline["duration_seconds"] * fps)
    if total > 216000:
        raise ValueError("Preview exceeds frame budget")
    cursor = 0
    result = []
    for row in timeline["intervals"]:
        start = math.ceil(row["start"] * fps)
        end = min(total, math.ceil(row["end"] * fps))
        if start < cursor or end <= start:
            raise ValueError("Animation interval cannot be represented at requested fps")
        if start > cursor:
            result.append((None, start-cursor))
        result.append((row["file"], end-start))
        cursor = end
    if cursor < total:
        result.append((None,total-cursor))
    return result


def render(trace, frames_dir, timing, bindings, slide, audio, output, fps=30):
    timeline = compile_timeline(trace, frames_dir, timing, bindings)
    schedule = frame_schedule(timeline, fps)
    slide, audio, output = map(Path, (slide,audio,output))
    if output.exists():
        raise FileExistsError(output)
    metadata = json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(audio)]))
    if not any(s["codec_type"] == "audio" for s in metadata["streams"]):
        raise ValueError("Narration audio stream missing")
    duration = float(metadata["format"]["duration"])
    if not math.isfinite(duration) or abs(duration-timeline["duration_seconds"]) > .15:
        raise ValueError("Audio duration differs from measured timeline")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        clips = []
        for index,(filename,count) in enumerate(schedule):
            source = Path(frames_dir)/filename if filename else slide
            clip = root/f"clip_{index:05d}.mp4"
            run(["ffmpeg","-v","error","-y","-loop","1","-framerate",str(fps),
                 "-i",str(source),"-vf",
                 "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1",
                 "-frames:v",str(count),"-an","-c:v","libx264","-preset","veryfast",
                 "-pix_fmt","yuv420p",str(clip)])
            clips.append(clip)
        listing = root/"clips.txt"
        listing.write_text("".join("file '"+p.name+"'\n" for p in clips),encoding="utf-8")
        candidate = root/"candidate.mp4"
        run(["ffmpeg","-v","error","-y","-f","concat","-safe","1","-i",str(listing),
             "-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
             "-movflags","+faststart",str(candidate)])
        info = json.loads(run(["ffprobe","-v","error","-count_frames","-show_streams","-of","json",str(candidate)]))
        video = next(s for s in info["streams"] if s["codec_type"]=="video")
        if int(video["nb_read_frames"]) != sum(count for _,count in schedule):
            raise ValueError("Rendered frame count mismatch")
        run(["ffmpeg","-v","error","-xerror","-i",str(candidate),"-f","null","-"])
        import shutil
        shutil.copyfile(candidate,output)
    return {"frames":sum(count for _,count in schedule),"fps":fps,
            "source_verified":False,"manual_review_required":True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("trace","frames_dir","timing","bindings","slide","audio","output"):
        parser.add_argument(name)
    parser.add_argument("--fps",type=int,default=30)
    a = parser.parse_args()
    def load(p):
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    print(json.dumps(render(load(a.trace),a.frames_dir,load(a.timing),load(a.bindings),
                            a.slide,a.audio,a.output,a.fps)))


if __name__ == "__main__":
    main()
