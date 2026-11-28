#!/usr/bin/env python3
"""Insert Azure-narrated DSU animation chapters after the corresponding PPT exercise sections."""
import argparse,json,subprocess
from pathlib import Path
def run(c):
 p=subprocess.run(c,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr[-3000:])
 return p.stdout.strip()
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def compose(base,timing_dir,chapter_dir,out):
 base=Path(base);td=Path(timing_dir);cd=Path(chapter_dir);out=Path(out)
 # Insert each animation chapter after its corresponding exercise section.
 mapping=[(15,'relatives'),(21,'fencing'),(27,'food_chain'),(33,'galaxy')]
 times={i:json.loads((td/f'slide_{i:03d}.json').read_text(encoding='utf-8'))['duration_seconds'] for i in range(1,35)}
 starts={};cursor=0.0
 for i in range(1,35):starts[i]=cursor;cursor+=float(times[i])
 base_duration=float(probe(base)['format']['duration'])
 if abs(base_duration-cursor)>.35:raise ValueError('Base course duration differs from measured slide timing')
 segments=[];last=0.0
 for slide,name in mapping:
  cut=starts[slide]+float(times[slide])
  if cut>last:segments.append(('base',last,cut))
  chapter=cd/f'{name}_azure_narrated.mp4'
  if not chapter.exists():raise FileNotFoundError(chapter)
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
 m=probe(out);vs=next(x for x in m['streams'] if x['codec_type']=='video');aud=next(x for x in m['streams'] if x['codec_type']=='audio')
 if (vs['width'],vs['height'],vs['r_frame_rate'])!=(1920,1080,'30/1'):raise ValueError('Final 1080p30 validation failed')
 run(['ffmpeg','-v','error','-xerror','-i',str(out),'-f','null','-'])
 report={'status':'PASS','file':out.name,'duration_seconds':float(m['format']['duration']),'inserted_chapters':[x[1] for x in mapping],'resolution':'1920x1080','fps':30,'video_codec':vs['codec_name'],'audio_codec':aud['codec_name'],'full_decode':'PASS','manual_review_required':True,'auto_approved':False}
 out.with_suffix('.qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report
def main():
 p=argparse.ArgumentParser()
 for x in ['base','timings-dir','chapters-dir','out']:p.add_argument('--'+x,required=True)
 a=p.parse_args();print(json.dumps(compose(a.base,a.timings_dir,a.chapters_dir,a.out),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
