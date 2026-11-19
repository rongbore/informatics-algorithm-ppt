#!/usr/bin/env python3
"""Extract actual reference PDF font/color/layout statistics; no OCR or image inference."""
import argparse,collections,json,fitz
from pathlib import Path

def analyze(pdf):
    d=fitz.open(pdf)
    pages=[];fonts=collections.Counter();text_colors=collections.Counter();draw_fills=collections.Counter()
    for k,p in enumerate(d):
        spans=[s for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
        for s in spans:
            fonts[(s['font'],round(s['size'],2))]+=len(s['text'])
            text_colors['#%06X'%s['color']]+=len(s['text'])
        for dr in p.get_drawings():
            if dr['fill'] is not None:
                draw_fills['#'+''.join('%02X'%round(255*c) for c in dr['fill'])]+=1
        bbox=fitz.Rect(*p.get_text('blocks')[0][:4]) if p.get_text('blocks') else fitz.Rect(0,0,0,0)
        pages.append({'page':k+1,'rect_pt':list(p.rect),'text_spans':len(spans),'draw_paths':len(p.get_drawings()),'first_text_bbox_pt':list(bbox)})
    return {'source':Path(pdf).name,'total_pages':len(d),'metadata':d.metadata,'fonts_weighted':fonts.most_common(15),'text_colors_weighted':text_colors.most_common(15),'draw_fills':draw_fills.most_common(20),'pages':pages}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('pdf');ap.add_argument('--out')
    a=ap.parse_args();result=analyze(a.pdf);data=json.dumps(result,ensure_ascii=False,indent=2)
    if a.out:Path(a.out).write_text(data,encoding='utf-8')
    else:print(data)
