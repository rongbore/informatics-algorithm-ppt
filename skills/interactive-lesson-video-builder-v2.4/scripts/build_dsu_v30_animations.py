#!/usr/bin/env python3
"""Build source-hash-bound 1080p state frames and preview MP4s for the four DSU exercises."""
import argparse,hashlib,json,math,subprocess,tempfile,shutil
from pathlib import Path
from pptx import Presentation
from PIL import Image,ImageDraw,ImageFont
W,H,FPS=1920,1080,30
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
NAVY=(35,75,107);INK=(38,52,69);BLUE=(59,95,152);GREEN=(65,130,100);GOLD=(246,184,73);PALE=(232,244,251);WHITE=(255,255,255);BG=(250,250,250);MUTED=(100,116,139)
def F(n,b=False):return ImageFont.truetype(BOLD if b and Path(BOLD).exists() else FONT,n)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a):subprocess.run(a,check=True,capture_output=True)
def canvas(title,subtitle,step,total,caption):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
 d.rounded_rectangle((54,42,1866,160),24,fill=WHITE,outline=(220,230,239),width=2)
 d.text((92,64),title,font=F(48,True),fill=NAVY);d.text((94,124),subtitle,font=F(25),fill=MUTED)
 d.rounded_rectangle((54,920,1866,1024),20,fill=(239,245,250));d.text((88,945),caption,font=F(28,True),fill=INK)
 d.text((1630,950),f'{step:02d}/{total:02d}',font=F(25,True),fill=BLUE)
 d.rounded_rectangle((88,1000,1832,1009),4,fill=(210,220,230));d.rounded_rectangle((88,1000,88+1744*step/max(total,1),1009),4,fill=(74,176,223))
 return im,d
def tree(d,parent,active=(),changed=(),origin=(960,380),width=1450):
 n=len(parent);children={i:[] for i in range(1,n+1)};roots=[]
 for i,p in enumerate(parent,1):
  if i==p:roots.append(i)
  else:children[p].append(i)
 def leaves(v):return max(1,sum(leaves(c) for c in children[v]))
 total=sum(leaves(r) for r in roots);unit=width/max(total,1);pos={}
 def place(v,left,depth):
  span=leaves(v)*unit;pos[v]=(origin[0]-width/2+left+span/2,origin[1]+depth*105);cur=left
  for c in children[v]:place(c,cur,depth+1);cur+=leaves(c)*unit
 cur=0
 for r in roots:place(r,cur,0);cur+=leaves(r)*unit
 for v,p in enumerate(parent,1):
  if v==p:continue
  x,y=pos[v];xx,yy=pos[p];color=GREEN if v in changed else BLUE
  d.line((x,y-25,xx,yy+25),fill=color,width=7)
  a=math.atan2(yy-y,xx-x);d.polygon([(xx,yy),(xx-25*math.cos(a)+10*math.sin(a),yy-25*math.sin(a)-10*math.cos(a)),(xx-25*math.cos(a)-10*math.sin(a),yy-25*math.sin(a)+10*math.cos(a))],fill=color)
 for v,(x,y) in pos.items():
  root=parent[v-1]==v;d.ellipse((x-34,y-34,x+34,y+34),fill=GOLD if v in active else ((218,237,226) if root else PALE),outline=NAVY,width=4)
  d.text((x,y),str(v),font=F(30,True),fill=INK,anchor='mm')
  if root:d.text((x,y-54),'根',font=F(20,True),fill=GREEN,anchor='mm')
def array_panel(d,parent,caption):
 n=len(parent);cell=min(170,1500/n);start=(W-cell*n)/2
 for i,p in enumerate(parent,1):
  x=start+(i-1)*cell;d.rounded_rectangle((x,690,x+cell-12,790),12,fill=PALE,outline=(190,210,225),width=2)
  d.text((x+(cell-12)/2,715),f'p[{i}]',font=F(22),fill=MUTED,anchor='mm');d.text((x+(cell-12)/2,758),str(p),font=F(32,True),fill=NAVY,anchor='mm')
 d.text((110,845),caption,font=F(26,True),fill=GREEN)
def save_frames(frames,out,meta):
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);fd=out.parent/(out.stem+'_frames')
 if fd.exists():shutil.rmtree(fd)
 fd.mkdir();rows=[]
 for i,im in enumerate(frames):
  p=fd/f'frame_{i:03d}.png';im.save(p);rows.append({'index':i,'file':p.name,'sha256':sha(p)})
 with tempfile.TemporaryDirectory() as td:
  td=Path(td);lst=td/'list.txt'
  lst.write_text(''.join(f"file '{(fd/r['file']).as_posix()}'\nduration 1.7\n" for r in rows[:-1])+f"file '{(fd/rows[-1]['file']).as_posix()}'\n",encoding='utf-8')
  run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(lst),'-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20','-movflags','+faststart',str(out)])
 pr=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out)],capture_output=True,text=True,check=True).stdout);v=next(x for x in pr['streams'] if x['codec_type']=='video')
 assert (v['width'],v['height'],v['r_frame_rate'])==(1920,1080,'30/1')
 meta.update({'file':out.name,'sha256':sha(out),'frames_dir':fd.name,'frame_files':rows,'resolution':'1920x1080','fps':30,'duration_seconds':float(pr['format']['duration']),'state_frames':len(rows),'render_status':'PASS','source_verified':True,'manual_review_required':True,'auto_approved':False})
 out.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');return meta
def relatives(out,source):
 p=list(range(1,7));events=[('初始化：六个人各自独立',p.copy(),[],[],'六个独立集合')]
 for a,b in [(1,2),(1,5),(3,4),(5,2),(1,3)]:
  def root(x):
   while p[x-1]!=x:x=p[x-1]
   return x
  ra,rb=root(a),root(b);before=p.copy()
  if ra!=rb:p[rb-1]=ra
  events.append((f'登记关系 {a} 与 {b}',p.copy(),[a,b],[i for i,(x,y) in enumerate(zip(before,p),1) if x!=y],f'合并后集合数：{len({root(i) for i in range(1,7)})}'))
 events.append(('查询：比较两个节点的根',p.copy(),[3],[],'判断同组必须比较根节点'))
 frames=[]
 for i,(t,pa,hi,ch,cap) in enumerate(events,1):
  im,d=canvas('练习一｜亲戚：连通关系与集合查询',t,i,len(events),cap);d.rounded_rectangle((70,220,1850,830),24,fill=WHITE,outline=(220,230,239),width=2);tree(d,pa,hi,ch);array_panel(d,pa,cap);frames.append(im)
 return save_frames(frames,out,{'exercise':'relatives','animation_id':'relatives','source_slides':[13,14,15],'narration_event_ids':[f'dsu_relatives_{i:02d}' for i in range(7)],'source_sha256':source,'event_count':len(events)})
def fencing(out,source):
 pts={1:(0,5),2:(10,5),3:(5,0),4:(5,10),5:(6,7),6:(8,6),7:(8,4)};p=list(range(8));events=[('七头牛的坐标与初始集合',p.copy(),[],None,'坐标接近不代表同组')]
 for a,b in [(1,2),(2,3),(3,4),(5,6),(7,6)]:
  def root(x):
   while p[x]!=x:x=p[x]
   return x
  ra,rb=root(a),root(b)
  if ra!=rb:p[rb]=ra
  events.append((f'合并关系 {a}—{b}',p.copy(),[a,b],None,'按题给关系合并集合'))
 groups={}
 for i in pts:groups.setdefault(root(i),[]).append(i)
 boxes=[]
 for ids in groups.values():
  xs=[pts[i][0] for i in ids];ys=[pts[i][1] for i in ids];boxes.append((min(xs),max(xs),min(ys),max(ys),2*((max(xs)-min(xs))+(max(ys)-min(ys))),ids))
 assert sorted(b[4] for b in boxes)==[10,40]
 events.append(('按最终根统计四个坐标极值',p.copy(),[],boxes,'两组周长分别 40 与 10，答案 10'))
 frames=[]
 for i,(t,pa,hi,bs,cap) in enumerate(events,1):
  im,d=canvas('练习二｜修建围栏：分组与坐标极值',t,i,len(events),cap);d.rounded_rectangle((70,220,1850,830),24,fill=WHITE,outline=(220,230,239),width=2)
  x0,y0,scale=260,760,54;d.line((x0,y0-600,x0,y0),fill=INK,width=4);d.line((x0,y0,x0+650,y0),fill=INK,width=4)
  for k in range(0,11,2):
   xx=x0+k*scale;yy=y0-k*scale;d.line((xx,y0-550,xx,y0),fill=(232,238,243),width=2);d.line((x0,yy,x0+600,yy),fill=(232,238,243),width=2)
  if bs:
   for a,b,c,e,per,ids in bs:d.rectangle((x0+a*scale,y0-e*scale,x0+b*scale,y0-c*scale),outline=BLUE if len(ids)==4 else GREEN,width=8);d.text((x0+(a+b)*scale/2,y0-e*scale-36),f'周长 {per}',font=F(24,True),fill=BLUE if len(ids)==4 else GREEN,anchor='mm')
  for node,(x,y) in pts.items():
   color=BLUE if node<=4 else GREEN;xx=x0+x*scale;yy=y0-y*scale;d.ellipse((xx-16,yy-16,xx+16,yy+16),fill=GOLD if node in hi else color,outline=WHITE,width=3);d.text((xx+22,yy-28),str(node),font=F(25,True),fill=INK)
  d.text((1050,360),'A = {1, 2, 3, 4}',font=F(32,True),fill=BLUE);d.text((1050,430),'B = {5, 6, 7}',font=F(32,True),fill=GREEN)
  if bs:d.text((1050,560),'min(40, 10) = 10',font=F(42,True),fill=(198,69,69))
  frames.append(im)
 return save_frames(frames,out,{'exercise':'fencing','animation_id':'fencing','source_slides':[16,17,18,19,20,21],'narration_event_ids':[f'dsu_fence_{i:02d}' for i in range(7)],'source_sha256':source,'event_count':len(events),'verified_groups':[[1,2,3,4],[5,6,7]],'perimeters':[40,10],'answer':10})
def food_chain(out,source):
 events=[
  ("初始化：每只动物拆成 S、P、E 三类槽位","每只动物维护本类 S、猎物类 P、天敌类 E 三个关系槽位",0),
  ("D=1：同类关系的三组对应合并","S(x)=S(y)；P(x)=P(y)；E(x)=E(y)",1),
  ("D=2：x 吃 y 的三组对应关系","P(x)=S(y)；S(x)=E(y)；E(x)=P(y)",2),
  ("接受前检查已有关系","同类冲突：S(x) 与 P(y) 或 E(y)；捕食冲突：S(x) 与 S(y) 或 P(y)",3),
  ("课件原样例 1：n=5，检查三句话","A 类 {1,2,3,5}；B 类 {4}；A 吃 B；三句话同时成立，假话数 0",4),
  ("课件原样例 2：n=3，检查两句话","课件变式第一句改为 2 1 4，编号 4 越界；按课件复算，假话数 1",5),
  ("能由已有关系推出的话也要接受","只要不与已接受约束冲突，就接受；不能把可推出的真话重复计假",6)
 ]
 frames=[]
 for i,(label,detail,mode) in enumerate(events,1):
  im,d=canvas('练习三｜食物链：三类关系与冲突检测',label,i,len(events),detail)
  d.rounded_rectangle((70,220,1850,830),24,fill=WHITE,outline=(220,230,239),width=2)
  titles=['本类 S(x)','猎物类 P(x)','天敌类 E(x)']
  for col,title in enumerate(titles):
   xx=350+col*610;d.text((xx,300),title,font=F(34,True),fill=NAVY,anchor='mm')
   for animal in range(1,4):
    yy=420+(animal-1)*115
    d.rounded_rectangle((xx-100,yy-36,xx+100,yy+36),14,fill=GOLD if mode in (1,2) else PALE,outline=BLUE,width=3)
    d.text((xx,yy),f'{title[0]}({animal})',font=F(25,True),fill=INK,anchor='mm')
  if mode==1:
   for y in [420,535,650]:
    for col in range(3):
     xx=350+col*610;d.line((xx+105,y,xx+505,y),fill=GREEN,width=5)
   d.text((960,770),'同类：三类槽位分别对应相等',font=F(29,True),fill=GREEN,anchor='mm')
  elif mode==2:
   pairs=[((350,535),(960,420)),((350,420),(1570,650)),((350,650),(960,535))]
   for (x1,y1),(x2,y2) in pairs:d.line((x1+105,y1,x2-105,y2),fill=GREEN,width=6)
   d.text((960,770),'捕食方向：P(x)→S(y)，S(x)→E(y)，E(x)→P(y)',font=F(26,True),fill=GREEN,anchor='mm')
  elif mode==3:
   d.rounded_rectangle((300,390,1620,680),18,fill=(255,246,230),outline=GOLD,width=3)
   d.text((960,470),'先检查矛盾，再执行合并',font=F(40,True),fill=INK,anchor='mm')
   d.text((960,560),'每句话最多计假一次',font=F(34,True),fill=(198,69,69),anchor='mm')
  elif mode==4:
   d.rounded_rectangle((250,390,1670,680),18,fill=PALE,outline=BLUE,width=3)
   d.text((960,455),'A 类：{1, 2, 3, 5}',font=F(42,True),fill=BLUE,anchor='mm')
   d.text((960,535),'B 类：{4}',font=F(42,True),fill=GREEN,anchor='mm')
   d.text((960,615),'A 吃 B    |    三句话成立    |    假话数 = 0',font=F(32,True),fill=INK,anchor='mm')
  elif mode==5:
   d.rounded_rectangle((250,390,1670,680),18,fill=(255,246,230),outline=GOLD,width=3)
   d.text((960,465),'n = 3    |    两句话',font=F(38,True),fill=INK,anchor='mm')
   d.text((960,550),'变式：2  1  4    →    编号 4 越界',font=F(34,True),fill=(198,69,69),anchor='mm')
   d.text((960,625),'按课件复算：假话数 = 1',font=F(32,True),fill=INK,anchor='mm')
  elif mode==6:
   d.rounded_rectangle((250,390,1670,680),18,fill=(232,245,236),outline=GREEN,width=3)
   d.text((960,485),'能推出 ≠ 矛盾',font=F(46,True),fill=GREEN,anchor='mm')
   d.text((960,575),'可由已有关系推出的真话，仍然接受',font=F(32,True),fill=INK,anchor='mm')
  frames.append(im)
 return save_frames(frames,out,{'exercise':'food_chain','animation_id':'food_chain','source_slides':[22,23,24,25,26,27],'narration_event_ids':[f'dsu_food_{i:02d}' for i in range(7)],'source_sha256':source,'event_count':len(events),'source_grounded_examples':{'sample_1':{'n':5,'class_A':[1,2,3,5],'class_B':[4],'relation':'A eats B','false_count':0},'sample_2':{'n':3,'statement_count':2,'variant_first_statement':[2,1,4],'invalid_reason':'index 4 out of range','false_count':1}},'representation':'3n slots S/P/E'})
def galaxy(out,source):
 p=list(range(9));off=[0]*9;sz=[1]*9;p[2]=1;off[2]=1;sz[1]=2;p[7]=6;off[7]=1;p[8]=6;off[8]=2;sz[6]=3
 p[1]=6;off[1]=sz[6];sz[6]+=sz[1];sz[1]=0
 merged=(p[1:].copy(),off[1:].copy(),sz[1:].copy())
 total=off[2]+off[1];p[2]=6;off[2]=total
 events=[('两支队伍：[1,2] 与 [6,7,8]',[1,2,6,7,8],0,'接收队伍长度为 3，移来队伍长度为 2'),('执行 M 2 7：整队接到队尾',[6,7,8,1,2],1,'p[1]=6，d[1]=3，sz[6]=5'),('查找船 2：路径压缩',[6,7,8,1,2],2,'船 2 到队首偏移为 4'),('压缩示例旧链 2→3→4',[2,3,4],3,'两条父边权值分别为 1'),('压缩示例新链 2→4',[2,4],4,'新边权为 2，实体位置不变')]
 frames=[]
 for i,(label,order,mode,cap) in enumerate(events,1):
  im,d=canvas('练习四｜银河英雄传说：带权并查集',label,i,len(events),cap);d.rounded_rectangle((70,220,1850,830),24,fill=WHITE,outline=(220,230,239),width=2)
  if mode<3:
   for j,node in enumerate(order):
    x=360+j*245;y=420;d.rounded_rectangle((x-75,y-75,x+75,y+75),24,fill=GOLD if node in ([1,2] if mode==0 else [1,2,6,7,8]) else PALE,outline=BLUE,width=4);d.text((x,y-8),str(node),font=F(42,True),fill=NAVY,anchor='mm');d.text((x,y+43),f'位置 {j}',font=F(19),fill=MUTED,anchor='mm')
    if j<4:d.line((x+78,y,x+165,y),fill=GREEN,width=7)
   d.text((960,650),'父数组：'+str(merged[0]),font=F(24),fill=INK,anchor='mm');d.text((960,710),'偏移：'+str(merged[1]),font=F(24),fill=INK,anchor='mm')
  else:
   nodes=order;pos={node:(560+j*400,430) for j,node in enumerate(nodes)}
   for a,b in zip(nodes,nodes[1:]):
    x,y=pos[a];xx,yy=pos[b];d.line((x+55,y,xx-55,yy),fill=GREEN if mode==4 else BLUE,width=8);d.text(((x+xx)//2,yy-55),'+1' if mode==3 else '+2',font=F(25,True),fill=GREEN,anchor='mm')
   for node,(x,y) in pos.items():d.ellipse((x-48,y-48,x+48,y+48),fill=GOLD if node==2 else PALE,outline=BLUE,width=4);d.text((x,y),str(node),font=F(38,True),fill=NAVY,anchor='mm')
   d.text((960,620),'d[2] = 1 + 1 = 2' if mode==4 else 'd[2] + d[3] = 1 + 1',font=F(34,True),fill=INK,anchor='mm')
  frames.append(im)
 return save_frames(frames,out,{'exercise':'galaxy','animation_id':'galaxy','source_slides':[28,29,30,31,32,33],'narration_event_ids':[f'dsu_galaxy_{i:02d}' for i in range(5)],'source_sha256':source,'event_count':len(events),'queue_after_merge':[6,7,8,1,2],'node_2_offset':4,'path_compression_offset':2})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pptx',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();ppt=Path(a.pptx);prs=Presentation(str(ppt))
 if len(prs.slides)!=34:raise ValueError('This verified DSU profile expects the 34-slide source deck')
 text=' '.join(sh.text for sl in prs.slides for sh in sl.shapes if getattr(sh,'has_text_frame',False))
 for token in ['亲戚','修建围栏','食物链','银河英雄传说']:
  if token not in text:raise ValueError(f'Source deck missing required section: {token}')
 source=sha(ppt);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 rows=[relatives(out/'01_亲戚_动态演示.mp4',source),fencing(out/'02_修建围栏_动态演示.mp4',source),food_chain(out/'03_食物链_动态演示.mp4',source),galaxy(out/'04_银河英雄传说_动态演示.mp4',source)]
 report={'schema_version':'3.0.0','source_pptx':ppt.name,'source_sha256':source,'slide_count':34,'animations':rows,'manual_review_required':True,'auto_approved':False}
 (out/'animation_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
