#!/usr/bin/env python3
"""Insert Azure-narrated DSU chapters and rebuild a synchronized course SRT."""
import argparse,json,re,subprocess
from pathlib import Path
def run(c):
 p=subprocess.run(c,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr[-3000:])
 return p.stdout.strip()
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def stamp(t):
 ms=round(float(t)*1000);h=ms//3600000;ms%=3600000;m=ms//60000;ms%=60000;s=ms//1000;ms%=1000
 return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
def read_srt(path):
 if not Path(path).exists():return []
 raw=Path(path).read_text(encoding='utf-8-sig');rows=[]
 for block in re.split(r'\n\s*\n',raw.strip()):
  lines=[x for x in block.splitlines() if x.strip()]
  if len(lines)<3:continue
  mt=re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})',lines[1])
  if not mt:continue
  def sec(x):
   h,m,z=x.split(':');s,ms=z.split(',');return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
  rows.append((sec(mt.group(1)),sec(mt.group(2)),'\n'.join(lines[2:])))
 return rows
def compose(base,timing_dir,chapter_dir,chapter_timing_dir,slide_srt_dir,out,srt_out):
 base=Path(base);td=Path(timing_dir);cd=Path(chapter_dir);ct=Path(chapter_timing_dir);sd=Path(slide_srt_dir);out=Path(out)
 mapping=[(15,'relatives',101),(21,'fencing',102),(27,'food_chain',103),(33,'galaxy',104)]
 times={i:json.loads((td/f'slide_{i:03d}.json').read_text(encoding='utf-8'))['duration_seconds'] for i in range(1,35)}
 starts={};cursor=0.0
 for i in range(1,35):starts[i]=cursor;cursor+=float(times[i])
 base_meta=probe(base);base_duration=float(base_meta['format']['duration'])
 if abs(base_duration-cursor)>.35:raise ValueError('Base video duration differs from measured slide timing')
 segments=[];last=0.0;chapter_rows={}
 for slide,name,synthetic in mapping:
  cut=starts[slide]+float(times[slide])
  if cut>last:segments.append(('base',last,cut))
  chapter=cd/f'{name}_azure_narrated.mp4'
  if not chapter.exists():raise FileNotFoundError(chapter)
  chapter_timing=json.loads((ct/f'slide_{synthetic:03d}.json').read_text(encoding='utf-8'))
  actual=float(probe(chapter)['format']['duration'])
  if abs(actual-float(chapter_timing['duration_seconds']))>.2:raise ValueError(f'{name} chapter audio/video timing mismatch')
  chapter_rows[name]=(chapter_timing,actual)
  segments.append(('chapter',chapter,None));last=cut
 if last<base_duration:segments.append(('base',last,base_duration))
 inputs=['-i',str(base)];chidx={};graph=[];v=[];a=[]
 base_count=sum(x[0]=='base' for x in segments)
 graph += [f'[0:v]split={base_count}'+''.join(f'[bv{i}]' for i in range(base_count)),f'[0:a]asplit={base_count}'+''.join(f'[ba{i}]' for i in range(base_count))]
 bi=0
 for i,seg in enumerate(segments):
  if seg[0]=='base':
   _,start,end=seg
   graph.append(f'[bv{bi}]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS,fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v{i}]')
   graph.append(f'[ba{bi}]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]');bi+=1
  else:
   path=seg[1];idx=len(chidx)+1;chidx[str(path)]=idx;inputs+=['-i',str(path)]
   graph.append(f'[{idx}:v]fps=30,scale=1920:1080,format=yuv420p,setpts=PTS-STARTPTS[v{i}]')
   graph.append(f'[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]')
  v.append(f'[v{i}]');a.append(f'[a{i}]')
 graph.append(''.join(v+a)+f'concat=n={len(segments)}:v=1:a=1[vout][aout]')
 out.parent.mkdir(parents=True,exist_ok=True)
 run(['ffmpeg','-v','error','-y',*inputs,'-filter_complex',';'.join(graph),'-map','[vout]','-map','[aout]','-c:v','libx264','-preset','medium','-crf','19','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)])
 meta=probe(out);vs=next(x for x in meta['streams'] if x['codec_type']=='video');aud=next(x for x in meta['streams'] if x['codec_type']=='audio')
 if (vs['width'],vs['height'],vs['r_frame_rate'])!=(1920,1080,'30/1'):raise ValueError('Final 1080p30 validation failed')
 run(['ffmpeg','-v','error','-xerror','-i',str(out),'-f','null','-'])
 # Rebase base slide subtitles and insert chapter cue subtitles at the same media offsets.
 subtitles=[];seq=1;inserted=0.0;insert_map={x[0]:(x[1],x[2]) for x in mapping}
 for slide in range(1,35):
  local=starts[slide]+inserted
  for a0,b0,text in read_srt(sd/f'slide_{slide:03d}.srt'):
   subtitles.append(f'{seq}\n{stamp(local+a0)} --> {stamp(local+b0)}\n{text}');seq+=1
  if slide in insert_map:
   name,synthetic=insert_map[slide];timing,_=chapter_rows[name]
   for event in timing['speech_events']:
    phrases=event.get('phrases',[])
    if phrases:
     for phrase in phrases:
      subtitles.append(f'{seq}\n{stamp(local+phrase["start"])} --> {stamp(local+phrase["end"])}\n{phrase["text"]}');seq+=1
    else:
     subtitles.append(f'{seq}\n{stamp(local+event["start"])} --> {stamp(local+event["end"])}\n{event["text"]}');seq+=1
   inserted+=float(timing['duration_seconds'])
 Path(srt_out).parent.mkdir(parents=True,exist_ok=True)
 Path(srt_out).write_text('\n\n'.join(subtitles)+'\n',encoding='utf-8')
 report={'status':'PASS','file':out.name,'duration_seconds':float(meta['format']['duration']),'inserted_seconds':round(inserted,3),'inserted_chapters':[x[1] for x in mapping],'resolution':'1920x1080','fps':30,'video_codec':vs['codec_name'],'audio_codec':aud['codec_name'],'full_decode':'PASS','subtitle_cues':len(subtitles),'manual_review_required':True,'auto_approved':False}
 out.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report
def main():
 p=argparse.ArgumentParser()
 for x in ['base','timings-dir','chapters-dir','chapter-timings-dir','slide-srt-dir','out','srt-out']:p.add_argument('--'+x,required=True)
 x=p.parse_args();print(json.dumps(compose(x.base,x.timings_dir,x.chapters_dir,x.chapter_timings_dir,x.slide_srt_dir,x.out,x.srt_out),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
