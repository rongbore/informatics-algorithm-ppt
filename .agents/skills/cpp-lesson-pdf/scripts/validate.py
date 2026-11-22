#!/usr/bin/env python3
"""Validate a C++ lesson PDF skill package and compiled PDF; not a visual substitute."""
import argparse
from pathlib import Path
import re
import subprocess
import shutil
import sys

FILES = [
    'SKILL.md', 'manifest.yaml', 'README.md',
    'references/PROMPT.md', 'references/MASTER-PROMPT.md',
    'references/REVERSE-ENGINEERING.md', 'references/PDF-STYLE-GUIDE.md',
    'references/CODE-COMMENT-RULES.md', 'references/QA-CHECKLIST.md',
    'templates/main.tex', 'templates/lesson-style.sty',
    'templates/diagram-styles.tex', 'examples/code/toposort_demo.cpp',
    'scripts/build.sh', 'scripts/build.ps1', 'scripts/validate.py',
    'references/DEEP-REASONING-STEPS.md', 'references/VISUAL-DERIVATION-STANDARD.md',
    'examples/derivations/tree_knapsack_merge.json',
    'examples/derivations/tree_knapsack_visual.tex', 'scripts/trace_dp_merge.py',
]

def check_files(root, errs):
    for rel in FILES:
        if not (root / rel).is_file():
            errs.append('Missing package file: ' + rel)
    for src in (root / 'examples/code').glob('*.cpp'):
        code = src.read_text('utf-8')
        if not re.search(r'//[^\n]*[\u4e00-\u9fff]',code):
            errs.append(f'Chinese core comments missing from source: {src}')
        if not all(token in code for token in ('#include', 'main(', 'cout')):
            errs.append(f'Example C++ source is incomplete: {src}')

def check_tex(root, errs):
    tex = (root/'templates/main.tex').read_text('utf-8')
    if not re.search(r'\\LessonCodeFile\s*\{',tex):
        errs.append('main.tex does not call code-file inclusion macro')
    for match in re.finditer(r'\\LessonCodeFile\s*\{([^}]+)\}', tex):
        code_path = (root/'templates'/match.group(1)).resolve()
        if not code_path.is_file(): errs.append(f'Missing linked C++ file: {code_path}')

def check_pdf(pdf, errs):
    if not pdf.is_file():
        errs.append(f'PDF not found: {pdf}'); return
    try:
        import fitz
        doc = fitz.open(pdf)
        if not doc.is_pdf or len(doc) == 0:
            errs.append('Cannot open nonempty PDF');return
        alltxt = '\n'.join(page.get_text() for page in doc)
        for i,p in enumerate(doc):
            if abs(p.rect.width-595.28)>2 or abs(p.rect.height-841.89)>2:
                errs.append(f'Page {i+1} is not A4')
            if len(p.get_text().strip())<30:
                errs.append(f'Page {i+1}: too little extractable text')
            for span in (s for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']):
                x0,y0,x1,y1=span['bbox']
                if x0<-2 or x1>p.rect.width+2 or y0<-2 or y1>p.rect.height+2:
                    errs.append(f'Page {i+1}: text span outside page ({span["text"][:30]})')
        for bad in ['<MINTED>', '<LISTINGS>', 'PLACEHOLDER', '�']:
            if bad in alltxt:errs.append(f'Unrendered/malformed marker in PDF: {bad}')
        if '核心' not in alltxt and '前置' not in alltxt:
            errs.append('PDF text may not include Chinese core comments')
        if '#include' not in alltxt or 'main' not in alltxt:
            errs.append('PDF does not visibly include actual C++ code')
        print(f'PDF: {len(doc)} pages, {len(alltxt)} extracted characters, A4 checked')
    except ImportError:
        if shutil.which('pdftotext'):
            cp=subprocess.run(['pdftotext',str(pdf),'-'],capture_output=True,text=True,errors='replace')
            text=cp.stdout
            if cp.returncode or not text.strip():errs.append('pdftotext failed')
            if '<MINTED>' in text:errs.append('Unrendered <MINTED> code')
        else:
            errs.append('Cannot inspect PDF: install PyMuPDF or pdftotext')
    except Exception as e:
        errs.append(f'PDF inspection failed: {e}')

def check_cpp(root,errs):
    compiler=shutil.which('g++')
    if not compiler:
        print('SKIP: g++ unavailable; example code was not checked')
        return
    src=root/'examples/code/toposort_demo.cpp'
    cp=subprocess.run([compiler,'-std=c++17','-fsyntax-only',str(src)],capture_output=True,text=True)
    if cp.returncode:errs.append('C++ syntax check failed: '+cp.stderr[-600:])
    else:print('C++ demo: g++ -std=c++17 syntax check passed')

def check_visual_derivation(root, errs):
    """Check that the teaching j/k transition table can be recreated."""
    trace = root / 'scripts/trace_dp_merge.py'
    data = root / 'examples/derivations/tree_knapsack_merge.json'
    if not trace.exists() or not data.exists():
        return
    result = subprocess.run([sys.executable, str(trace), '--data', str(data)],
                            capture_output=True, text=True, timeout=20)
    if result.returncode != 0:
        errs.append('DP visual trace check failed: ' + result.stderr[-500:])
    elif '倒序合并的最终状态' not in result.stdout:
        errs.append('DP visual trace output did not include expected state summary')
    else:
        print('DP visual derivation: verified transition table and forward-order counterexample')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument('--pdf')
    ap.add_argument('--require-code-comments',action='store_true')
    ap.add_argument('--check-demo-code',action='store_true')
    args=ap.parse_args()
    root=Path(args.root).resolve();errs=[]
    check_files(root,errs)
    check_visual_derivation(root,errs)
    if args.require_code_comments:check_tex(root,errs)
    if args.pdf:check_pdf(Path(args.pdf),errs)
    if args.check_demo_code:check_cpp(root,errs)
    if errs:
        print('VALIDATION FAILED')
        for e in errs:print(' -',e)
        return 1
    print('VALIDATION PASSED (still render and visually inspect all pages)')
    return 0

if __name__=='__main__':sys.exit(main())
