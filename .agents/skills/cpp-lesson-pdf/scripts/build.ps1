$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Join-Path $root 'templates'
$output = Join-Path $root 'output'
New-Item -ItemType Directory -Force -Path $output | Out-Null
Push-Location $source
try {
  1..2 | ForEach-Object {
    & xelatex '-interaction=nonstopmode' '-halt-on-error' "-output-directory=$output" 'main.tex'
    if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX compilation failed. Check output/main.log.' }
  }
} finally { Pop-Location }
Write-Host "PDF created: $output\main.pdf"
