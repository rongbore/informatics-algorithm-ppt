import argparse, json, shutil, subprocess
from pathlib import Path

def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace")
    if p.returncode: raise RuntimeError(p.stderr[-2000:])
    return p.stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--video",required=True)
    ap.add_argument("--qa-json",required=True)
    a=ap.parse_args()
    video=Path(a.video); report=json.loads(Path(a.qa_json).read_text(encoding="utf-8-sig"))
    if not video.exists(): raise SystemExit("Video file missing")
    ffprobe=shutil.which("ffprobe")
    if not ffprobe: raise SystemExit("ffprobe missing")
    data=json.loads(run([ffprobe,"-v","error","-show_streams","-show_format","-of","json",str(video)]))
    streams=data.get("streams",[])
    v=next((s for s in streams if s.get("codec_type")=="video"),None)
    au=next((s for s in streams if s.get("codec_type")=="audio"),None)
    checks={"video_stream_present":v is not None,"audio_stream_present":au is not None,
            "resolution_1080p":bool(v and v.get("width")==1920 and v.get("height")==1080),
            "qa_requires_manual_review":report.get("manual_review_required") is True,
            "not_auto_approved":report.get("auto_approved") is False}
    result={"video":str(video),"checks":checks,"passed":all(checks.values()),"manual_review_required":True,
            "note":"This validates media streams and metadata only. It cannot certify semantic subtitle overlap, code legibility or algorithm correctness."}
    out=Path(a.qa_json).with_name("final_media_checks.json")
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result["passed"]: raise SystemExit(2)
if __name__=="__main__": main()
