#!/usr/bin/env python3
"""Render one verified DSU state frame per measured Azure narration cue."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
def run(c):
 p=subprocess.run(c,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr[-2500:])
 return p.stdout.strip()
def duration(p):return float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)]))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def render(anim,frames_dir,timing,audio,out,expected):
 if timing.get('tts_provider')!='azure_ai_speech':raise ValueError('Azure audio required')
 rows=anim['frame_files'];events=timing['speech_events']
 if len(rows)!=len(events) or len(expected)!=len(rows):raise ValueError('Each state needs exactly one narration cue')
 for i,(r,e,cue) in enumerate(zip(rows,events,expected)):
  if sha(Path(frames_dir)/r['file'])!=r['sha256']:raise ValueError('Frame hash mismatch')
  if e['event_id']!=anim['narration_event_ids'][i] or e['event_id']!=cue['event_id'] or e['text']!=cue['text']:raise ValueError('Narration cue mismatch')
  if i and e['start']<events[i-1]['end']:raise ValueError('Overlapping measured speech')
 if abs(duration(audio)-timing['duration_seconds'])>.15:raise ValueError('Audio duration mismatch')
 with tempfile.TemporaryDirectory() as td:
  td=Path(td);clips=[]
  for i,(r,e) in enumerate(zip(rows,events)):
   end=events[i+1]['start'] if i+1<len(events) else timing['duration_seconds'];span=end-e['start']
   if span<=0:raise ValueError('Invalid frame display duration')
   clip=td/f'f{i:03d}.mp4';run(['ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i',str(Path(frames_dir)/r['file']),'-t',f'{span:.6f}','-vf','format=yuv420p','-an','-c:v','libx264','-preset','veryfast','-crf','20',str(clip)]);clips.append(clip)
  lst=td/'clips.txt';lst.write_text(''.join(f"file '{p.name}'\n" for p in clips),encoding='utf-8')
  silent=td/'silent.mp4';run(['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i',str(lst),'-c','copy',str(silent)])
  out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
  run(['ffmpeg','-v','error','-y','-i',str(silent),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-shortest','-movflags','+faststart',str(out)])
 meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out)]));v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio')
 if (v['width'],v['height'],v['r_frame_rate'])!=(1920,1080,'30/1'):raise ValueError('1080p30 failed')
 if abs(float(meta['format']['duration'])-timing['duration_seconds'])>.2:raise ValueError('Chapter duration mismatch')
 run(['ffmpeg','-v','error','-xerror','-i',str(out),'-f','null','-'])
 return {'file':out.name,'sha256':sha(out),'duration_seconds':float(meta['format']['duration']),'resolution':'1920x1080','fps':30,'video_codec':v['codec_name'],'audio_codec':a['codec_name'],'full_decode':'PASS','manual_review_required':True,'auto_approved':False}
def main():
 p=argparse.ArgumentParser()
 for x in ['manifest','narration','timings-dir','audio-dir','out']:p.add_argument('--'+x,required=True)
 a=p.parse_args();m=json.loads(Path(a.manifest).read_text(encoding='utf-8'));n=json.loads(Path(a.narration).read_text(encoding='utf-8'));out=Path(a.out);reports=[]
 for i,anim in enumerate(m['animations']):
  slide=101+i;t=json.loads((Path(a.timings_dir)/f'slide_{slide:03d}.json').read_text(encoding='utf-8'));cue=next(x['events'] for x in n['animations'] if x['animation_id']==anim['animation_id'])
  reports.append(render(anim,Path(a.manifest).parent/anim['frames_dir'],t,Path(a.audio_dir)/f'slide_{slide:03d}.mp3',out/f'{anim["exercise"]}_azure_narrated.mp4',cue))
 (out/'chapter_qa.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(reports,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
