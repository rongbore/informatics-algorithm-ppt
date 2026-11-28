#!/usr/bin/env python3
"""Azure AI Speech drop-in generator for V2.4 phrase timing JSON."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from azure_speech_v30 import PROFILES,build_ssml,synthesize
def run(c):
 p=subprocess.run(c,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr[-2500:])
 return p.stdout.strip()
def duration(p):return float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)]))
def split(text):
 parts=[x.strip() for x in re.split(r'(?<=[。！？；：.!?;])',re.sub(r'\s+',' ',str(text or '')).strip()) if x.strip()]
 out=[];buf=''
 for x in parts:
  if buf and len(buf)>=12:out.append(buf);buf=x
  else:buf+=x
 if buf:out.append(buf)
 return [x for x in out if len(x)>=2]
def silence(ffmpeg,path,sec):
 if not path.exists():run([ffmpeg,'-y','-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t',f'{sec:.3f}','-c:a','pcm_s16le',str(path)])
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--timings-output');p.add_argument('--config',required=True);p.add_argument('--slides',nargs='*',type=int);p.add_argument('--all-slides',action='store_true');p.add_argument('--profile',choices=PROFILES,default='coach_excited');a=p.parse_args()
 data=json.loads(Path(a.input).read_text(encoding='utf-8-sig'));cfg=json.loads(Path(a.config).read_text(encoding='utf-8-sig'))
 if 'animations' in data:data={'slides':[{'slide':101+i,'events':x['events'],'slide_end_pause_seconds':0} for i,x in enumerate(data['animations'])]}
 ffmpeg=shutil.which('ffmpeg')
 if not ffmpeg or not shutil.which('ffprobe'):raise RuntimeError('FFmpeg and FFprobe required')
 out=Path(a.output);td=Path(a.timings_output or out/'timings');cache=out/'.azure_cache';out.mkdir(parents=True,exist_ok=True);td.mkdir(parents=True,exist_ok=True);cache.mkdir(exist_ok=True)
 selected={int(x['slide']) for x in data['slides']} if a.all_slides else set(a.slides or [])
 report={'provider':'azure_ai_speech','profile':a.profile,'completed':[],'failures':[]}
 for slide in data['slides']:
  no=int(slide['slide'])
  if no not in selected:continue
  pieces=[];speech=[];phrase_rows=[];pauses=[];cursor=0.0;charpos=0
  try:
   for ei,event in enumerate(slide.get('events',[]),1):
    kind=event.get('type','narration');eid=event.get('event_id',f's{no:03d}_e{ei:02d}')
    if kind=='pause':
     sec=float(event.get('duration_seconds',0) or 0)
     if sec>0:
      q=cache/f'silence_{int(sec*1000)}.wav';silence(ffmpeg,q,sec);d=duration(q);pieces.append(q);pauses.append({'event_id':eid,'kind':'explicit','start':round(cursor,3),'end':round(cursor+d,3)});cursor+=d
     continue
    original=str(event.get('text','')).strip();phrases=split(original)
    if not phrases:raise ValueError(f'Empty narration event: {eid}')
    event_start=cursor;event_phrases=[]
    for pi,phrase in enumerate(phrases):
     key=hashlib.sha256((a.profile+'\\n'+phrase).encode()).hexdigest();mp3=cache/(key+'.mp3');wav=cache/(key+'.wav')
     if not mp3.exists():synthesize(build_ssml(phrase,a.profile),mp3)
     if not wav.exists():run([ffmpeg,'-y','-i',str(mp3),'-ar','24000','-ac','1','-c:a','pcm_s16le',str(wav)])
     d=duration(wav);row={'event_id':eid,'phrase_index':pi,'type':kind,'text':phrase,'start':round(cursor,3),'end':round(cursor+d,3),'source_char_start':charpos,'source_char_end':charpos+len(re.sub(r'\\s+','',phrase))}
     event_phrases.append(row);phrase_rows.append(row);pieces.append(wav);cursor+=d;charpos+=len(re.sub(r'\\s+','',phrase))
     if pi<len(phrases)-1:
      ms=700 if re.search(r'[？?！!]',phrase) else 520 if re.search(r'[。；;]',phrase) else 260
      q=cache/f'pause_{ms}.wav';silence(ffmpeg,q,ms/1000);d=duration(q);pieces.append(q);pauses.append({'event_id':eid,'kind':'natural','start':round(cursor,3),'end':round(cursor+d,3)});cursor+=d
    speech.append({'event_id':eid,'type':kind,'text':original,'start':round(event_start,3),'end':round(cursor,3),'phrases':event_phrases})
    sec=float(event.get('thinking_seconds',0) or 0) if kind=='thinking_prompt' else float(event.get('pause_after_seconds',0) or 0)
    if sec>0:
     q=cache/f'pause_{int(sec*1000)}.wav';silence(ffmpeg,q,sec);d=duration(q);pieces.append(q);pauses.append({'event_id':eid,'kind':'thinking_prompt' if kind=='thinking_prompt' else 'explicit','start':round(cursor,3),'end':round(cursor+d,3)});cursor+=d
   end=float(slide.get('slide_end_pause_seconds',cfg['pacing'].get('slide_end_pause_seconds',3)))
   if end>0:
    q=cache/f'end_{int(end*1000)}.wav';silence(ffmpeg,q,end);d=duration(q);pieces.append(q);pauses.append({'event_id':None,'kind':'slide_end','start':round(cursor,3),'end':round(cursor+d,3)});cursor+=d
   if not pieces:raise ValueError('No narration events')
   lst=cache/f'concat_{no}.txt';lst.write_text(''.join("file '"+str(x.resolve()).replace("'","'\\''")+"'\n" for x in pieces),encoding='utf-8')
   wavout=out/f'slide_{no:03d}.wav';run([ffmpeg,'-y','-f','concat','-safe','0','-i',str(lst),'-c:a','pcm_s16le',str(wavout)])
   mp3out=out/f'slide_{no:03d}.mp3';run([ffmpeg,'-y','-i',str(wavout),'-codec:a','libmp3lame','-q:a','3',str(mp3out)]);wavout.unlink(missing_ok=True)
   actual=duration(mp3out);timing={'schema_version':'2.4.1','slide':no,'duration_seconds':round(actual,3),'alignment_mode':'measured_phrase_boundaries','speech_events':speech,'phrases':phrase_rows,'pauses':pauses,'tts_provider':'azure_ai_speech','voice_profile':a.profile}
   (td/f'slide_{no:03d}.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding='utf-8');report['completed'].append({'slide':no,'duration_seconds':actual,'phrases':len(speech)})
  except Exception as e:report['failures'].append({'slide':no,'error':str(e)})
 report['status']='COMPLETE' if not report['failures'] else 'INCOMPLETE';(out/'azure_tts_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 if report['failures']:raise SystemExit(2)
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
