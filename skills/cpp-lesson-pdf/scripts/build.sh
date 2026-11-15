#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/templates"
mkdir -p "$ROOT/output"
xelatex -interaction=nonstopmode -halt-on-error -output-directory="$ROOT/output" main.tex >/dev/null
xelatex -interaction=nonstopmode -halt-on-error -output-directory="$ROOT/output" main.tex >/dev/null
printf 'PDF created: %s\n' "$ROOT/output/main.pdf"
