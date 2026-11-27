param(
 [string]$SkillRoot=(Split-Path -Parent $PSScriptRoot),
 [string]$Narration="templates\narration_events_v2_2.json",
 [string]$Timeline="analysis\highlight_timeline.json",
 [string]$SlidesDir="rendered\slides",
 [int[]]$Slides=@(1,20,40,60,80)
)
$ErrorActionPreference="Stop"
Set-Location $SkillRoot
$Py=Join-Path $SkillRoot ".venv\Scripts\python.exe"
if(!(Test-Path $Py)){throw "Python venv missing: $Py"}
foreach($p in @($Narration,$Timeline,$SlidesDir)){if(!(Test-Path $p)){throw "Required input missing: $p"}}
$BuildDir="build\v2_3"
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
$V23Narration=Join-Path $BuildDir "narration_events_v2_3.json"
& $Py scripts\migrate_narration_v2_3.py --input $Narration --output $V23Narration --overrides config\thinking_difficulty_overrides.json --config config\video_ux_v2_3.json
if($LASTEXITCODE -ne 0){throw "V2.3 narration migration failed"}
& $Py scripts\generate_audio_v2_3.py --input $V23Narration --output audio_v2_3 --timings-output audio_v2_3\timings --config config\video_ux_v2_3.json --slides $Slides
if($LASTEXITCODE -ne 0){throw "V2.3 audio generation failed"}
& $Py scripts\render_lesson_v2_3.py --slides $SlidesDir --audio audio_v2_3 --speech-timings audio_v2_3\timings --timeline $Timeline --output video\v2_3_pilot_5slides.mp4 --qa qa_v2_3 --ux-config config\video_ux_v2_3.json --only-slides $Slides
if($LASTEXITCODE -ne 0){throw "V2.3 rendering failed"}
& $Py scripts\qa_v2_3.py --video video\v2_3_pilot_5slides.mp4 --qa-json qa_v2_3\qa_report_v2_3.json
if($LASTEXITCODE -ne 0){throw "V2.3 media QA failed"}
Write-Host "Pilot completed. Review video\v2_3_pilot_5slides.mp4 and qa_v2_3." -ForegroundColor Green
