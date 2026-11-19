$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Join-Path $root 'templates'
$out = Join-Path $root 'output'
New-Item -ItemType Directory -Force -Path $out | Out-Null
if (-not (Get-Command xelatex -ErrorAction SilentlyContinue)) { throw 'XeLaTeX not installed or absent from PATH' }
if (-not (Get-Command latexminted -ErrorAction SilentlyContinue)) { throw 'latexminted not installed; requires minted/Pygments' }
Push-Location $source
try {
    for ($pass = 1; $pass -le 3; $pass++) {
        $log = Join-Path $out "build-pass-$pass.log"
        & xelatex '-shell-escape' '-interaction=nonstopmode' '-halt-on-error' "-output-directory=$out" 'main.tex' *> $log
        if ($LASTEXITCODE -ne 0) { throw "XeLaTeX failed on pass $pass. See $log" }
        if ($pass -ge 2) {
            if (Get-Command pdftotext -ErrorAction SilentlyContinue) {
                $txt = (& pdftotext (Join-Path $out 'main.pdf') '-') -join "`n"
                if ($txt -notmatch '<MINTED>|<LISTINGS>') { break }
                if ($pass -eq 3) { throw 'Unresolved code placeholder in PDF' }
            } else { break }
        }
    }
} finally { Pop-Location }
& python (Join-Path $root 'scripts/validate.py') '--root' $root '--pdf' (Join-Path $out 'main.pdf') '--require-code-comments' '--check-demo-code'
if ($LASTEXITCODE -ne 0) { throw 'PDF validation failed' }
Write-Host "Generated: $out\main.pdf"
