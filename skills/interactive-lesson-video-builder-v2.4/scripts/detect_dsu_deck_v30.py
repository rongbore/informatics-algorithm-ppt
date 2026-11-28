import argparse,json
from pathlib import Path
from pptx import Presentation
def main():
 p=argparse.ArgumentParser();p.add_argument("--pptx",required=True);a=p.parse_args();prs=Presentation(a.pptx)
 text=" ".join(sh.text for slide in prs.slides for sh in slide.shapes if getattr(sh,"has_text_frame",False))
 required=["亲戚","修建围栏","食物链","银河英雄传说"]
 result={"family":"dsu" if len(prs.slides)==34 and all(x in text for x in required) else "generic","slide_count":len(prs.slides),"matched_sections":[x for x in required if x in text]}
 print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
