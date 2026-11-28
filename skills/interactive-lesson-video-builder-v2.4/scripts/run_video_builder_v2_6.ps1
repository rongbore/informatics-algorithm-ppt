param(
 [Parameter(Mandatory=$true)][ValidateSet("Prepare","Render")][string]$Phase,
 [Parameter(Mandatory=$true)][string]$Pptx,
 [string]$OutputDir=".\lesson_video_output",
 [string]$NarrationJson,
 [string]$AlignmentDecisions,
 [string]$StoryboardJson
)
$ErrorActionPreference="Stop"
$Engine=Split-Path -Parent $PSScriptRoot
$Scripts=Join-Path $Engine "scripts"
$Config=Join-Path $Engine "config\video_ux_v2_4.json"
$PptxPath=(Resolve-Path -LiteralPath $Pptx).Path
$Root=[IO.Path]::GetFullPath($OutputDir)
$Slides=Join-Path $Root "rendered\slides"
$Build=Join-Path $Root "build\v2_6"
$Audio=Join-Path $Root "audio"
$Timings=Join-Path $Audio "timings"
$Regions=Join-Path $Build "regions.json"
$Narration=Join-Path $Build "narration_events.json"
$Context=Join-Path $Build "alignment_context.json"
$Decisions=Join-Path $Build "alignment_decisions_verified.json"
$Plan=Join-Path $Build "alignment_plan.json"
$Compiled=Join-Path $Build "compiled_alignment.json"
$Subtitles=Join-Path $Root "subtitles"
$Videos=Join-Path $Root "video"
$Qa=Join-Path $Root "qa"
$Font="C:\Windows\Fonts\msyh.ttc"

trap {
 $failure=$_.Exception.Message
 try {
  $failed=@{version="2.6.0";status="INCOMPLETE";generated_at=(Get-Date).ToString("o");error=$failure;manual_review_required=$true;auto_approved=$false}
  $failed|ConvertTo-Json -Depth 5|Set-Content (Join-Path $Root "delivery_manifest.json") -Encoding UTF8
 } catch {}
 Write-Host ("INCOMPLETE: "+$failure) -ForegroundColor Red
 exit 1
}

function NeedFile($p,$label){if(-not(Test-Path -LiteralPath $p -PathType Leaf)){throw "$label missing: $p"}}
function Mkdir($p){New-Item -ItemType Directory -Force -Path $p|Out-Null}
function Run($exe,[string[]]$Arguments,$label){
 Write-Host "";Write-Host "[$label]" -ForegroundColor Cyan
 & $exe @Arguments
 if($LASTEXITCODE -ne 0){throw "$label failed with exit code $LASTEXITCODE"}
}
foreach($p in @($Slides,$Build,$Audio,$Timings,$Subtitles,$Videos,$Qa)){Mkdir $p}
$python=(Get-Command python -ErrorAction Stop).Source
foreach($tool in @("ffmpeg","ffprobe","powershell")){if(-not(Get-Command $tool -ErrorAction SilentlyContinue)){throw "Install $tool and add it to PATH."}}
& $python -c "import sys,pptx,edge_tts; assert sys.version_info >= (3,10)"
if($LASTEXITCODE -ne 0){throw ("Install dependencies: python -m pip install -r "+(Join-Path $Engine "requirements-v2.4.txt"))}
NeedFile $Config "Video configuration"

if($Phase -eq "Prepare"){
 if(-not $NarrationJson){throw "Skill agent must internally author narration JSON and pass -NarrationJson; user input remains one PPTX."}
 NeedFile $NarrationJson "Skill-authored narration"
 Copy-Item $PptxPath (Join-Path $Root "source.pptx") -Force
 Copy-Item (Resolve-Path $NarrationJson).Path $Narration -Force
 Run "powershell.exe" @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $Scripts "render_slides_v2_4.ps1"),"-Pptx",$PptxPath,"-OutputDir",$Slides) "Export PowerPoint slides"
 Run $python @((Join-Path $Scripts "extract_slide_regions_v2_4.py"),"--pptx",$PptxPath,"--slides-dir",$Slides,"--output",$Regions) "Extract slide regions"
 Run $python @((Join-Path $Scripts "generate_audio_v2_4.py"),"--input",$Narration,"--output",$Audio,"--timings-output",$Timings,"--config",$Config,"--all-slides") "Generate neural TTS and measured timings"
 Run $python @((Join-Path $Scripts "prepare_alignment_inputs_v2_4.py"),"--regions",$Regions,"--narration",$Narration,"--timings-dir",$Timings,"--audio-dir",$Audio,"--output",$Context) "Prepare machine-hashed alignment context"
 Write-Host "PREPARE COMPLETE. Skill agent must now create verified alignment decisions and storyboard JSON from the context and slide previews." -ForegroundColor Green
 Write-Host ("Context: "+$Context)
 exit 0
}

NeedFile $Regions "Regions manifest"
NeedFile $Narration "Narration events"
NeedFile $Context "Alignment context"
NeedFile $AlignmentDecisions "Verified decisions"
NeedFile $StoryboardJson "Storyboard JSON"
Copy-Item (Resolve-Path $AlignmentDecisions).Path $Decisions -Force
Copy-Item (Resolve-Path $StoryboardJson).Path (Join-Path $Build "storyboard.json") -Force
$finalize=Join-Path $Scripts "finalize_alignment_plan_v2_4.py"
$compile=Join-Path $Scripts "compile_alignment_v2_4.py"
$render=Join-Path $Scripts "render_lesson_v2_4.py"
$validate=Join-Path $Scripts "validate_full_video_v2_4.py"
Run $python @($finalize,"--context",$Context,"--decisions",$Decisions,"--output",$Plan) "Finalize alignment"
Run $python @($compile,"--regions",$Regions,"--narration",$Narration,"--alignment-plan",$Plan,"--timings-dir",$Timings,"--audio-dir",$Audio,"--output",$Compiled) "Compile complete alignment"

# Select representative slides by actual slide content, then fill gaps evenly.
$m=Get-Content $Regions -Raw -Encoding UTF8|ConvertFrom-Json
$rows=@($m.slides)
$pilot=[Collections.Generic.List[int]]::new()
$groups=@(
 @("课程目标","学习目标","本节课","导入"),
 @("定义","概念","原理","性质","知识点"),
 @("#include","int main","vector","cout","cin","代码"),
 @("例题","样例","模拟","推导","输入","输出"),
 @("练习","思考","总结","小结","作业")
)
foreach($group in $groups){
 $winner=$null;$best=0
 foreach($row in $rows){
  $n=[int]$row.slide;if($pilot.Contains($n)){continue}
  $txt=(@($row.regions|ForEach-Object{$_.text}) -join " ");$score=0
  foreach($word in $group){if($txt.Contains($word)){$score++}}
  if($score -gt $best){$best=$score;$winner=$n}
 }
 if($null -ne $winner){$pilot.Add([int]$winner)}
}
foreach($n in @(1,[Math]::Ceiling($rows.Count*.25),[Math]::Ceiling($rows.Count*.5),[Math]::Ceiling($rows.Count*.75),$rows.Count)){
 if($pilot.Count -ge 5){break};if(-not $pilot.Contains([int]$n)){$pilot.Add([int]$n)}
}
$pilot=@($pilot|Sort-Object|Select-Object -First 5)
$pilotCompiled=Join-Path $Build "compiled_alignment_pilot.json"
$pilotCompileArgs=@($compile,"--regions",$Regions,"--narration",$Narration,"--alignment-plan",$Plan,"--timings-dir",$Timings,"--audio-dir",$Audio,"--output",$pilotCompiled,"--slides")+$pilot
Run $python $pilotCompileArgs "Compile representative pilot"
$pilotVideo=Join-Path $Videos "pilot_internal.mp4";$pilotSubs=Join-Path $Subtitles "pilot";Mkdir $pilotSubs
$pilotRenderArgs=@($render,"--slides",$Slides,"--audio",$Audio,"--speech-timings",$Timings,"--alignment-report",$pilotCompiled,"--output",$pilotVideo,"--qa",(Join-Path $Qa "pilot"),"--ux-config",$Config,"--subtitle-dir",$pilotSubs,"--font-file",$Font,"--only-slides")+$pilot
Run $python $pilotRenderArgs "Render internal pilot"
$pilotReport=Join-Path (Join-Path $Qa "pilot") "qa_report_v2_4_alpha4.json"
Run $python @($validate,"--video",$pilotVideo,"--qa-report",$pilotReport,"--audio-dir",$Audio,"--timings-dir",$Timings,"--subtitle-dir",$pilotSubs,"--output",(Join-Path (Join-Path $Qa "pilot") "validation.json")) "Validate internal pilot"

$fullVideo=Join-Path $Videos "lesson_full.mp4";$fullSubs=Join-Path $Subtitles "full";Mkdir $fullSubs
Run $python @($render,"--slides",$Slides,"--audio",$Audio,"--speech-timings",$Timings,"--alignment-report",$Compiled,"--output",$fullVideo,"--qa",(Join-Path $Qa "full"),"--ux-config",$Config,"--subtitle-dir",$fullSubs,"--font-file",$Font) "Render full course"
$fullQa=Join-Path $Qa "full"
Run $python @($validate,"--video",$fullVideo,"--qa-report",(Join-Path $fullQa "qa_report_v2_4_alpha4.json"),"--audio-dir",$Audio,"--timings-dir",$Timings,"--subtitle-dir",$fullSubs,"--output",(Join-Path $fullQa "validation.json")) "Validate full course"

# Merge slide-level SRT files while renumbering cues.
# Export a readable teacher script and a measured phrase/pause timeline.
$narrationData=Get-Content $Narration -Raw -Encoding UTF8|ConvertFrom-Json
$narrationLines=[Collections.Generic.List[string]]::new()
foreach($slide in $narrationData.slides){
 $narrationLines.Add(("第"+$slide.slide+"页"))
 foreach($event in $slide.events){
  if($event.type -eq "pause"){continue}
  $narrationLines.Add(("["+[string]$event.type+"] "+[string]$event.text))
 }
 $narrationLines.Add("")
}
$narrationText=Join-Path $Root "narration_script.txt"
[IO.File]::WriteAllLines($narrationText,$narrationLines,[Text.UTF8Encoding]::new($false))
$timelineRows=[Collections.Generic.List[object]]::new()
foreach($timingFile in (Get-ChildItem $Timings -Filter "slide_*.json" -File|Sort-Object Name)){
 $timing=Get-Content $timingFile.FullName -Raw -Encoding UTF8|ConvertFrom-Json
 foreach($event in $timing.speech_events){
  $timelineRows.Add([pscustomobject]@{slide=$timing.slide;event_id=$event.event_id;phrase_index=$event.phrase_index;kind=$event.type;text=$event.text;start_seconds=$event.start;end_seconds=$event.end})
 }
 foreach($pause in $timing.pauses){
  $timelineRows.Add([pscustomobject]@{slide=$timing.slide;event_id=$pause.event_id;phrase_index=$null;kind=("pause_"+$pause.kind);text="";start_seconds=$pause.start;end_seconds=$pause.end})
 }
}
$timelineCsv=Join-Path $Root "measured_timeline.csv"
$timelineRows|Sort-Object slide,start_seconds|Export-Csv -LiteralPath $timelineCsv -NoTypeInformation -Encoding UTF8

$nl=[Environment]::NewLine;$merged=[Collections.Generic.List[string]]::new();$index=1
foreach($file in (Get-ChildItem $fullSubs -Filter "slide_*.srt" -File|Sort-Object Name)){
 $blocks=(Get-Content $file.FullName -Raw -Encoding UTF8)-split "(?:\r?\n){2,}"
 foreach($block in $blocks){
  $lines=@($block -split "\r?\n"|Where-Object{$_ -ne ""})
  if($lines.Count -lt 3){continue};$lines[0]=[string]$index;$merged.Add(($lines -join $nl));$index++
 }
}
$srt=Join-Path $Root "lesson_full.srt"
[IO.File]::WriteAllText($srt,($merged -join ($nl+$nl))+$nl,[Text.UTF8Encoding]::new($false))
$manifest=@{version="2.6.0";status="COMPLETE";video="video/lesson_full.mp4";subtitles="lesson_full.srt";storyboard="build/v2_6/storyboard.json";narration="narration_script.txt";timeline="measured_timeline.csv";narration_events="build/v2_6/narration_events.json";regions="build/v2_6/regions.json";qa="qa/full/validation.json";manual_review_required=$true;auto_approved=$false}
$manifest|ConvertTo-Json -Depth 5|Set-Content (Join-Path $Root "delivery_manifest.json") -Encoding UTF8
$zip=Join-Path $Root "lesson_video_production_package.zip"
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path (Join-Path $Root "*") -DestinationPath $zip -CompressionLevel Optimal
Write-Host "COMPLETE: $fullVideo"
Write-Host "SUBTITLES: $srt"
Write-Host "PACKAGE: $zip"
Write-Host "Manual semantic review remains required."
