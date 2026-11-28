"""Azure AI Speech SSML profiles and secure REST synthesis helper."""
import argparse,hashlib,json,os,subprocess,time,urllib.error,urllib.request
from pathlib import Path
from xml.sax.saxutils import escape
PROFILES={
 "coach_excited":{"voice":"zh-CN-YunjianNeural","style":"sports-commentary-excited","rate":"+2%","pitch":"+1st","styledegree":"1.15"},
 "coach_balanced":{"voice":"zh-CN-YunjianNeural","style":"sports-commentary","rate":"-2%","pitch":"+0st","styledegree":"1.0"}}
def build_ssml(text,profile):
 if profile not in PROFILES: raise ValueError("Unknown Azure voice profile")
 p=PROFILES[profile]
 return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN"><voice name="{p["voice"]}"><mstts:express-as style="{p["style"]}" styledegree="{p["styledegree"]}"><prosody rate="{p["rate"]}" pitch="{p["pitch"]}">{escape(text)}</prosody></mstts:express-as></voice></speak>')
def get_endpoint():
 endpoint=os.getenv("AZURE_SPEECH_ENDPOINT","").strip()
 if endpoint:return endpoint.rstrip("/")
 region=os.getenv("AZURE_SPEECH_REGION","").strip()
 if not region:raise RuntimeError("Missing AZURE_SPEECH_REGION")
 return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
def synthesize(ssml,out_path,retries=3):
 key=os.getenv("AZURE_SPEECH_KEY","").strip()
 if not key:raise RuntimeError("Missing AZURE_SPEECH_KEY; configure local environment or GitHub Actions Secrets")
 req=urllib.request.Request(get_endpoint(),data=ssml.encode(),method="POST",headers={"Ocp-Apim-Subscription-Key":key,"Content-Type":"application/ssml+xml","X-Microsoft-OutputFormat":"audio-24khz-48kbitrate-mono-mp3","User-Agent":"interactive-lesson-video-builder-v3"})
 last=None
 for i in range(retries):
  try:
   with urllib.request.urlopen(req,timeout=90) as r:data=r.read()
   if not data:raise RuntimeError("Azure returned empty audio")
   Path(out_path).parent.mkdir(parents=True,exist_ok=True);Path(out_path).write_bytes(data)
   return {"path":str(out_path),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
  except urllib.error.HTTPError as e:
   last=RuntimeError(f"Azure Speech HTTP {e.code}: {e.read(300).decode('utf-8','replace')}")
   if e.code not in (429,500,502,503,504):break
  except Exception as e:last=e
  time.sleep(2**i)
 raise RuntimeError(f"Azure synthesis failed: {last}")
def main():
 p=argparse.ArgumentParser();p.add_argument("--sample-text",required=True);p.add_argument("--out",required=True);p.add_argument("--profiles",nargs="*",default=list(PROFILES));p.add_argument("--dry-run",action="store_true");a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True);rows=[]
 for profile in a.profiles:
  ssml=build_ssml(a.sample_text,profile);(out/f"{profile}.ssml").write_text(ssml,encoding="utf-8")
  row={"profile":profile,"voice":PROFILES[profile]["voice"],"style":PROFILES[profile]["style"],"ssml":"PASS"}
  if a.dry_run:row["audio"]="NOT_RUN"
  else:
   result=synthesize(ssml,out/f"{profile}.mp3");row.update(result)
   d=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(out/f"{profile}.mp3")],capture_output=True,text=True,check=True).stdout.strip();row["duration_seconds"]=float(d)
  rows.append(row)
 (out/"azure_voice_audition_report.json").write_text(json.dumps({"provider":"Azure AI Speech","profiles":rows,"human_listening_review_required":True},ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(rows,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
