#!/usr/bin/env bash
# Compile XeLaTeX twice; minted v3 can display <MINTED> placeholders on the first pass.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/templates"
OUT="$ROOT/output"
mkdir -p "$OUT"
command -v xelatex >/dev/null || { echo "XeLaTeX not found" >&2; exit 2; }
command -v latexminted >/dev/null || { echo "latexminted not found; install minted+Pygments" >&2; exit 2; }
for pass in 1 2 3; do
  echo "Compiling pass $pass ..."
  (cd "$SRC" && xelatex -shell-escape -interaction=nonstopmode -halt-on-error \
    -output-directory="$OUT" main.tex > "$OUT/build-pass-$pass.log" 2>&1) || {
      echo "XeLaTeX failed; see $OUT/build-pass-$pass.log" >&2
      tail -30 "$OUT/build-pass-$pass.log" >&2
      exit 1
    }
  if [ "$pass" -ge 2 ] && command -v pdftotext >/dev/null 2>&1; then
    if ! pdftotext "$OUT/main.pdf" - | grep -Eq '<MINTED>|<LISTINGS>'; then
      echo "Verified: code placeholders absent after pass $pass"
      break
    elif [ "$pass" -eq 3 ]; then
      echo "ERROR: unresolved code placeholder in compiled PDF" >&2; exit 3
    fi
  elif [ "$pass" -ge 2 ]; then
    # A third pass is safe when PDF text extraction is unavailable.
    break
  fi
done
python3 "$ROOT/scripts/validate.py" --root "$ROOT" --pdf "$OUT/main.pdf" --require-code-comments --check-demo-code
printf 'Generated: %s\n' "$OUT/main.pdf"
