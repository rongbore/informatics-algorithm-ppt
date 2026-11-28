param(
 [string]$ModelRoot = ".\models\sherpa-onnx-vits-zh-aishell3"
)
$ErrorActionPreference = "Stop"
$uri = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-icefall-zh-aishell3.tar.bz2"
$archive = Join-Path $env:TEMP "vits-icefall-zh-aishell3.tar.bz2"
New-Item -ItemType Directory -Force -Path $ModelRoot | Out-Null
Write-Host "Downloading the public Mandarin VITS model archive (about 115 MB compressed/unpacked model assets)." -ForegroundColor Cyan
Invoke-WebRequest -Uri $uri -OutFile $archive
tar -xjf $archive -C $ModelRoot
Remove-Item $archive -Force
$model = Get-ChildItem $ModelRoot -Recurse -Filter "model.onnx" | Select-Object -First 1
$tokens = Get-ChildItem $ModelRoot -Recurse -Filter "tokens.txt" | Select-Object -First 1
$lexicon = Get-ChildItem $ModelRoot -Recurse -Filter "lexicon.txt" | Select-Object -First 1
if (-not $model -or -not $tokens -or -not $lexicon) { throw "Expected model.onnx, tokens.txt and lexicon.txt were not found after extraction." }
$rules = @("phone.fst", "date.fst", "number.fst") | ForEach-Object { Get-ChildItem (Split-Path $model.FullName) -Filter $_ -File -ErrorAction SilentlyContinue }
Write-Host "Model files located:" -ForegroundColor Green
Write-Host "SHERPA_TTS_MODEL=$($model.FullName)"
Write-Host "SHERPA_TTS_TOKENS=$($tokens.FullName)"
Write-Host "SHERPA_TTS_LEXICON=$($lexicon.FullName)"
if ($rules.Count -gt 0) { Write-Host "SHERPA_TTS_RULE_FSTS=$($rules.FullName -join ',')" } else { Write-Warning "No phone/date/number FST files found; text normalization rules will be unavailable." }
Write-Host "Set these paths as local environment variables. Review the model's upstream license before redistribution or commercial use."
