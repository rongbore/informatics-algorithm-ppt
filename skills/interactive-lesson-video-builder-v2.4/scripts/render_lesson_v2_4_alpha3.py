import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from align_focus_v2_4 import validate_sources, align_slide

def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace")
    if p.returncode: raise RuntimeError(p.stderr[-5000:])
    return p.stdout.strip()

def probe_duration(ffprobe,path):
    return float(run([ffprobe,"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)]))

def image_size(ffprobe,path):
    data=json.loads(run([ffprobe,"-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",str(path)]))
    stream=data["streams"][0]
    return int(stream["width"]),int(stream["height"])

def srt_time(seconds):
    ms=max(0,int(round(seconds*1000))); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def compact(text):
    return re.sub(r"\s+","",str(text or ""))

def escpath(path):
    return str(Path(path).resolve()).replace("\\","/").replace(":","\\:").replace("'","\\'")

def thinking_intervals(timing):
    return [(float(p["start"]),float(p["end"])) for p in timing.get("pauses",[])
            if p.get("kind")=="thinking_prompt" and float(p["end"])>float(p["start"])]

def subtract_intervals(start,end,intervals):
    pieces=[(start,end)]
    for a,b in intervals:
        nxt=[]
        for x,y in pieces:
            if b<=x or a>=y: nxt.append((x,y))
            else:
                if a<x: nxt.append((x,a))
                if b<y: nxt.append((b,y))
        pieces=nxt
    return [(x,y) for x,y in pieces if y-x>=0.08]

def make_srt(timing,path,cfg):
    cues=[]; hidden=thinking_intervals(timing) if cfg.get("disable_during_thinking",True) else []
    max_chars=int(cfg.get("max_chars_per_line",16)); max_lines=int(cfg.get("max_lines",2))
    for event in timing.get("speech_events",[]):
        text=compact(event.get("text","")); start=float(event["start"]); end=float(event["end"])
        if not text or end<=start: continue
        blocks=[text[i:i+max_chars*max_lines] for i in range(0,len(text),max_chars*max_lines)]
        total=sum(len(x) for x in blocks); used=0; cursor=start
        for block in blocks:
            next_time=end if used+len(block)>=total else start+(end-start)*(used+len(block))/total
            lines=[block[i:i+max_chars] for i in range(0,len(block),max_chars)]
            caption="\n".join(lines[:max_lines])
            visible=subtract_intervals(cursor,next_time,hidden) if hidden else [(cursor,next_time)]
            for a,b in visible: cues.append((a,b,caption))
            cursor=next_time; used+=len(block)
    lines=[]
    for i,(a,b,text) in enumerate(cues,1): lines += [str(i),f"{srt_time(a)} --> {srt_time(b)}",text,""]
    path.write_text("\n".join(lines),encoding="utf-8-sig")
    return cues

def main():
    ap=argparse.ArgumentParser(description="V2.4 Alpha.3 phrase-aligned renderer (no ratio fallback)")
    ap.add_argument("--slides",required=True); ap.add_argument("--audio",required=True)
    ap.add_argument("--speech-timings",required=True); ap.add_argument("--timeline",required=True)
    ap.add_argument("--narration",required=True); ap.add_argument("--anchor-plan",required=True)
    ap.add_argument("--output",required=True); ap.add_argument("--qa",default="qa_v2_4")
    ap.add_argument("--ux-config",default="config/video_ux_v2_4.json")
    ap.add_argument("--subtitle-dir",default="subtitles_v2_4")
    ap.add_argument("--only-slides",nargs="*",type=int)
    ap.add_argument("--font-file",default=r"C:\Windows\Fonts\msyh.ttc")
    a=ap.parse_args()
    ffmpeg,ffprobe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    if not ffmpeg or not ffprobe: raise SystemExit("FFmpeg and FFprobe must be on PATH")
    cfg=json.loads(Path(a.ux_config).read_text(encoding="utf-8-sig"))
    timeline=json.loads(Path(a.timeline).read_text(encoding="utf-8-sig"))
    narration=json.loads(Path(a.narration).read_text(encoding="utf-8-sig"))
    anchor_plan=json.loads(Path(a.anchor_plan).read_text(encoding="utf-8-sig"))
    ts,ns,anchors=validate_sources(timeline,narration,anchor_plan)
    W,H,fps=[int(cfg["resolution"][k]) for k in ("width","height","fps")]
    band=int(cfg["layout"]["subtitle_band_height"]); content_h=H-band
    slides,audios,timings=Path(a.slides),Path(a.audio),Path(a.speech_timings)
    output=Path(a.output); output.parent.mkdir(parents=True,exist_ok=True)
    qa=Path(a.qa); qa.mkdir(parents=True,exist_ok=True)
    subtitle_dir=Path(a.subtitle_dir); subtitle_dir.mkdir(parents=True,exist_ok=True)
    selected=set(a.only_slides or []); clips=[]; rows=[]
    if selected and not selected <= set(ts): raise SystemExit("Unknown selected slides")
    with tempfile.TemporaryDirectory(prefix="lesson_v24a3_") as temp:
        temp=Path(temp); concat=output.parent/(output.stem+"_concat.txt")
        for item in timeline.get("slides",[]):
            number=int(item["slide"])
            if selected and number not in selected: continue
            image=slides/f"slide_{number:03d}.png"
            audio=audios/f"slide_{number:03d}.mp3"
            timing_file=timings/f"slide_{number:03d}.json"
            if not all(p.exists() for p in (image,audio,timing_file)):
                raise SystemExit(f"Missing input for slide {number}: {image}, {audio}, {timing_file}")
            timing=json.loads(timing_file.read_text(encoding="utf-8-sig"))
            duration=probe_duration(ffprobe,audio)
            srt=subtitle_dir/f"slide_{number:03d}.srt"
            cues=make_srt(timing,srt,cfg["subtitle"])
            iw,ih=image_size(ffprobe,image)
            scale=min(W/iw,content_h/ih); scaled_w,scaled_h=iw*scale,ih*scale
            offset_x,offset_y=(W-scaled_w)/2,(content_h-scaled_h)/2
            vf=[f"scale={W}:{content_h}:force_original_aspect_ratio=decrease",
                f"pad={W}:{content_h}:(ow-iw)/2:(oh-ih)/2:color=black",
                f"pad={W}:{H}:0:0:color={cfg['layout']['subtitle_band_color']}"]
            focus=cfg["focus"]; colors={"knowledge":focus["knowledge_color"],"code":focus["code_color"],"algorithm":focus["algorithm_color"]}
            alignment=align_slide(item,ns[number],timing,duration,anchors,float(focus.get("min_confidence",0.45)))
            matched=0; unmatched=0
            for row in alignment:
                event=item["events"][row["region_index"]]
                if row.get("reason")=="merged_duplicate_geometry":
                    continue
                if not focus.get("enabled",True) or not row["intervals"]:
                    unmatched+=1
                    continue
                x,y,w,h=event["bbox"]
                X=max(0,min(W-2,round(offset_x+x*scaled_w))); Y=max(0,min(content_h-2,round(offset_y+y*scaled_h)))
                BW=max(2,min(W-X,round(w*scaled_w))); BH=max(2,min(content_h-Y,round(h*scaled_h)))
                color=colors.get(event.get("kind"),colors["knowledge"])
                for interval in row["intervals"]:
                    start,end=interval["start"],interval["end"]
                    # Half-open interval avoids double focus at adjacent phrase boundaries.
                    enable=f"gte(t,{start:.3f})*lt(t,{end:.3f})"
                    vf.append(f"drawbox=x={X}:y={Y}:w={BW}:h={BH}:color={color}:t=fill:enable='{enable}'")
                    vf.append(f"drawbox=x={X}:y={Y}:w={BW}:h={BH}:color={focus['border_color']}:t={int(focus['border_width'])}:enable='{enable}'")
                matched+=1
            countdowns=thinking_intervals(timing)
            ccfg=cfg["countdown"]; font=Path(a.font_file)
            if not font.exists(): font=Path(ccfg.get("font_file",""))
            fontopt=f"fontfile='{escpath(font)}':" if font.exists() else ""
            if ccfg.get("enabled",True):
                for start,end in countdowns:
                    expr=f"ceil({end:.3f}-t)"
                    x=f"w-text_w-{int(cfg['layout'].get('countdown_right_margin',52))}"
                    y=f"h-text_h-{int(cfg['layout'].get('countdown_bottom_margin',27))}"
                    vf.append(f"drawtext={fontopt}text='%{{eif\\:{expr}\\:d}}':fontcolor={ccfg['font_color']}:fontsize={int(ccfg['font_size'])}:x={x}:y={y}:enable='between(t,{start:.3f},{end:.3f})'")
            sc=cfg["subtitle"]
            if sc.get("enabled",True):
                style=f"FontName={sc['font_name']},FontSize={int(sc['font_size'])},PrimaryColour={sc['color']},OutlineColour=&H80000000,BorderStyle=1,Outline={int(sc['outline'])},Shadow={int(sc['shadow'])},Alignment=2,MarginV={int(sc['margin_vertical'])},MarginR={int(sc.get('margin_right',190))}"
                vf.append(f"subtitles='{escpath(srt)}':force_style='{style}'")
            clip=temp/f"slide_{number:03d}.mp4"
            run([ffmpeg,"-y","-loop","1","-i",str(image),"-i",str(audio),"-t",f"{duration:.3f}",
                 "-vf",",".join(vf),"-r",str(fps),"-c:v","libx264","-preset","medium","-crf","20",
                 "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-shortest",str(clip)])
            clips.append(clip)
            rows.append({"slide":number,"duration_seconds":round(duration,2),"subtitle_cues":len(cues),
                         "thinking_intervals":len(countdowns),"thinking_seconds":round(sum(b-a for a,b in countdowns),2),
                         "matched_focus_regions":matched,"unmatched_focus_regions":unmatched,
                         "merged_duplicate_focus_regions":sum(1 for row in alignment if row.get("reason")=="merged_duplicate_geometry"),
                         "coordinate_transform":{"scale":round(scale,6),"offset_x":round(offset_x,2),"offset_y":round(offset_y,2)},
                         "focus_timing_modes":[row["mode"] for row in alignment if row["intervals"]],"focus_alignment":alignment})
            print(f"Rendered slide {number}: {duration:.2f}s, {len(cues)} subtitle cues, {len(countdowns)} numeric countdowns")
        if not clips: raise SystemExit("No slides selected")
        concat.write_text("\n".join("file '"+c.resolve().as_posix().replace("'","'\\''")+"'" for c in clips)+"\n",encoding="utf-8")
        run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(output)])
    meta=json.loads(run([ffprobe,"-v","error","-select_streams","v:0","-show_entries","stream=width,height,avg_frame_rate","-of","json",str(output)]))["streams"][0]
    report={"version":"2.4.0-alpha.3","slide_count":len(rows),"total_duration_seconds":round(sum(x["duration_seconds"] for x in rows),2),
            "resolution":f"{meta['width']}x{meta['height']}","fps":meta.get("avg_frame_rate"),
            "subtitle_alignment":"phrase-level measured timestamps, not word/phoneme forced alignment",
            "countdown_mode":"numeric_only_in_reserved_subtitle_band","auto_approved":False,"manual_review_required":True,
            "slides":rows,"limitations":["Focus overlays use phrase-level curated anchors or literal matches; unmatched regions are skipped.",
            "Not a full algorithm state simulation or word-level alignment.",
            "Frame-level overlap and instructional correctness require human review."]}
    (qa/"qa_report_v2_4_alpha3.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Video:",output); print("QA:",qa/"qa_report_v2_4_alpha3.json")
if __name__=="__main__": main()