#!/usr/bin/env python3
"""V3.1 unified Tencent-first/local-fallback TTS with measured phrase timings."""
from __future__ import annotations
import argparse, asyncio, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
from tencent_tts_v31 import free_tier_ready, synthesize_wav as tencent_synthesize
from local_sherpa_tts_v31 import LocalSherpaTTS

def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace")
    if p.returncode: raise RuntimeError(p.stderr[-3000:])
    return p.stdout.strip()

def duration(path, ffprobe):
    return float(run([ffprobe,"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)]))

def split_phrases(text, max_chars=140):
    text=re.sub(r"\s+"," ",str(text or "")).strip()
    if not text: return []
    sentences=[x.strip() for x in re.split(r"(?<=[。！？；：.!?;])",text) if x.strip()]
    result=[]
    for sentence in sentences:
        while len(sentence)>max_chars:
            cut=max((sentence.rfind(mark,0,max_chars+1) for mark in "，、, "),default=-1)
            if cut<20: cut=max_chars
            result.append(sentence[:cut+1].strip()); sentence=sentence[cut+1:].strip()
        if sentence: result.append(sentence)
    return [x for x in result if len(x)>=2]

def make_silence(ffmpeg,path,seconds):
    if not path.exists():
        run([ffmpeg,"-y","-f","lavfi","-i","anullsrc=r=24000:cl=mono","-t",f"{seconds:.3f}","-c:a","pcm_s16le",str(path)])

class ProviderRouter:
    def __init__(self, requested, cache, report):
        self.requested=requested; self.cache=cache; self.report=report; self.local=None
        self.cloud_ready, self.cloud_reason=free_tier_ready()
        if requested=="tencent" and not self.cloud_ready:
            self.report["provider_events"].append({"event":"cloud_preflight_blocked","reason":self.cloud_reason,"fallback":"local"})
    def synthesize(self,text,out_wav):
        key=hashlib.sha256((self.requested+"|"+text).encode("utf-8")).hexdigest()
        cached=self.cache/(key+".wav")
        if cached.exists() and cached.stat().st_size>1024:
            shutil.copy2(cached,out_wav);return {"provider":"cache"}
        if self.requested=="local":
            return self._local(text,out_wav)
        if self.requested=="tencent" and self.cloud_ready:
            try:
                result=tencent_synthesize(text,out_wav,
                    speed=float(os.getenv("TENCENT_TTS_SPEED","0.2")),
                    volume=float(os.getenv("TENCENT_TTS_VOLUME","0")),
                    emotion=os.getenv("TENCENT_TTS_EMOTION","").strip())
                shutil.copy2(out_wav,cached)
                self.report["provider_events"].append({"event":"cloud_phrase_synthesized","provider":"tencent_cloud","chars":len(text),"request_id":result.get("request_id"),"budget":result.get("budget")})
                return {"provider":"tencent_cloud","request_id":result.get("request_id")}
            except Exception as exc:
                # A failed cloud call is never retried and never switched to paid mode.
                self.report["provider_events"].append({"event":"cloud_call_failed","reason":str(exc),"fallback":"local"})
                self.cloud_ready=False
        return self._local(text,out_wav)
    def _local(self,text,out_wav):
        if self.local is None: self.local=LocalSherpaTTS()
        result=self.local.synthesize_wav(text,out_wav,speed=float(os.getenv("SHERPA_TTS_SPEED","1.0")))
        self.report["provider_events"].append({"event":"local_phrase_synthesized","provider":"local_sherpa_onnx","chars":len(text)})
        shutil.copy2(out_wav,self.cache/(hashlib.sha256(("local|"+text).encode("utf-8")).hexdigest()+".wav"))
        return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True);p.add_argument("--output",required=True);p.add_argument("--timings-output")
    p.add_argument("--config",required=True);p.add_argument("--slides",nargs="*",type=int);p.add_argument("--all-slides",action="store_true")
    p.add_argument("--provider",choices=["tencent","local"],default="tencent");p.add_argument("--profile",default="coach_excited")
    a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding="utf-8-sig"));cfg=json.loads(Path(a.config).read_text(encoding="utf-8-sig"))
    ffmpeg,ffprobe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    if not ffmpeg or not ffprobe: raise RuntimeError("FFmpeg and FFprobe are required")
    out=Path(a.output);timing_dir=Path(a.timings_output or out/"timings");cache=out/".v31_cache"
    out.mkdir(parents=True,exist_ok=True);timing_dir.mkdir(parents=True,exist_ok=True);cache.mkdir(exist_ok=True)
    if "animations" in data: data={"slides":[{"slide":101+i,"events":x["events"],"slide_end_pause_seconds":0} for i,x in enumerate(data["animations"])]}
    selected={int(s["slide"]) for s in data.get("slides",[])} if a.all_slides else set(a.slides or [])
    report={"schema_version":"3.1","requested_provider":a.provider,"actual_providers":[],"provider_events":[],"completed":[],"failures":[],"manual_review_required":True,"auto_approved":False}
    router=ProviderRouter(a.provider,cache,report)
    for slide in data.get("slides",[]):
        number=int(slide["slide"])
        if number not in selected: continue
        pieces=[];speech=[];phrase_rows=[];pauses=[];cursor=0.0;char_cursor=0
        try:
            for event_index,event in enumerate(slide.get("events",[]),1):
                kind=event.get("type","narration");event_id=event.get("event_id",f"s{number:03d}_e{event_index:02d}")
                if kind=="pause":
                    seconds=float(event.get("duration_seconds",0) or 0)
                    if seconds>0:
                        silence=cache/f"pause_{int(seconds*1000)}.wav";make_silence(ffmpeg,silence,seconds);d=duration(silence,ffprobe);pieces.append(silence)
                        pauses.append({"event_id":event_id,"kind":"explicit","start":round(cursor,3),"end":round(cursor+d,3)});cursor+=d
                    continue
                phrases=split_phrases(event.get("text",""))
                if not phrases: raise ValueError(f"Empty narration event: {event_id}")
                event_start=cursor;event_phrases=[]
                for phrase_index,phrase in enumerate(phrases):
                    key=hashlib.sha256((a.provider+"|"+phrase).encode("utf-8")).hexdigest()
                    wav=cache/(key+".wav")
                    if not wav.exists():
                        provider_info=router.synthesize(phrase,wav)
                        wav.with_suffix(".provider.json").write_text(json.dumps(provider_info,ensure_ascii=False,indent=2),encoding="utf-8")
                    else:
                        sidecar=wav.with_suffix(".provider.json")
                        provider_info=json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {"provider":"cached_provider_unknown"}
                        report["provider_events"].append({"event":"phrase_cache_reused","provider":provider_info.get("provider","cached_provider_unknown"),"chars":len(phrase)})
                    measured=duration(wav,ffprobe)
                    row={"event_id":event_id,"phrase_index":phrase_index,"type":kind,"text":phrase,"start":round(cursor,3),"end":round(cursor+measured,3),"source_char_start":char_cursor,"source_char_end":char_cursor+len(re.sub(r"\s+","",phrase))}
                    event_phrases.append(row);phrase_rows.append(row);pieces.append(wav);cursor+=measured;char_cursor+=len(re.sub(r"\s+","",phrase))
                    if phrase_index<len(phrases)-1:
                        ms=700 if re.search(r"[？?！!]",phrase) else 520 if re.search(r"[。；;]",phrase) else 260
                        silence=cache/f"natural_{ms}.wav";make_silence(ffmpeg,silence,ms/1000);d=duration(silence,ffprobe);pieces.append(silence)
                        pauses.append({"event_id":event_id,"kind":"natural","start":round(cursor,3),"end":round(cursor+d,3)});cursor+=d
                speech.append({"event_id":event_id,"type":kind,"text":str(event.get("text","")),"start":round(event_start,3),"end":round(cursor,3),"phrases":event_phrases})
                pause_after=float(event.get("thinking_seconds",event.get("pause_after_seconds",0)) or 0)
                if pause_after>0:
                    silence=cache/f"event_pause_{int(pause_after*1000)}.wav";make_silence(ffmpeg,silence,pause_after);d=duration(silence,ffprobe);pieces.append(silence)
                    pauses.append({"event_id":event_id,"kind":"thinking_prompt" if kind=="thinking_prompt" else "explicit","start":round(cursor,3),"end":round(cursor+d,3)});cursor+=d
            slide_pause=float(slide.get("slide_end_pause_seconds",cfg.get("pacing",{}).get("slide_end_pause_seconds",3)))
            if slide_pause>0:
                silence=cache/f"slide_end_{int(slide_pause*1000)}.wav";make_silence(ffmpeg,silence,slide_pause);d=duration(silence,ffprobe);pieces.append(silence)
                pauses.append({"event_id":None,"kind":"slide_end","start":round(cursor,3),"end":round(cursor+d,3)});cursor+=d
            if not pieces: raise RuntimeError("No audio segments")
            concat=cache/f"concat_{number:03d}.txt";concat.write_text("".join("file '"+str(x.resolve()).replace("'","'\\''")+"'\n" for x in pieces),encoding="utf-8")
            wavout=out/f"slide_{number:03d}.building.wav";run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(concat),"-c:a","pcm_s16le",str(wavout)])
            mp3=out/f"slide_{number:03d}.mp3";run([ffmpeg,"-y","-i",str(wavout),"-codec:a","libmp3lame","-q:a","3",str(mp3)]);wavout.unlink(missing_ok=True)
            actual=duration(mp3,ffprobe);providers=sorted({x.get("provider","unknown") for x in report["provider_events"] if x.get("event")=="cloud_phrase_synthesized"})
            timing={"schema_version":"2.4.1","slide":number,"duration_seconds":round(actual,3),"alignment_mode":"measured_phrase_boundaries","speech_events":speech,"phrases":phrase_rows,"pauses":pauses,"tts_provider":a.provider,"tts_engine_version":"3.1","human_review_required":True}
            (timing_dir/f"slide_{number:03d}.json").write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding="utf-8")
            report["completed"].append({"slide":number,"duration_seconds":actual,"phrases":len(phrase_rows)})
        except Exception as exc:
            report["failures"].append({"slide":number,"error":str(exc)})
            # stop after first provider/config failure; do not spin cloud requests
            break
    report["actual_providers"]=sorted({e.get("provider") for e in report["provider_events"] if e.get("provider")})
    report["status"]="COMPLETE" if not report["failures"] and len(report["completed"])==len(selected) else "INCOMPLETE"
    (out/"tts_v31_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if report["status"]!="COMPLETE": raise SystemExit(2)
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
