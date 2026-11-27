param([string]$SkillRoot="D:\Codex\skills\interactive-lesson-video-builder")
$ErrorActionPreference="Stop"
$Source=$PSScriptRoot
if(!(Test-Path $SkillRoot)){New-Item -ItemType Directory -Force -Path $SkillRoot | Out-Null}
$Backup=Join-Path $SkillRoot ("backup_before_v2_3_"+(Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
foreach($name in @("SKILL.md","scripts","config","templates","references","examples","README_V2.3.md")){
 $src=Join-Path $Source $name
 if(!(Test-Path $src)){continue}
 $dst=Join-Path $SkillRoot $name
 if(Test-Path $dst){Copy-Item $dst (Join-Path $Backup $name) -Recurse -Force}
 Copy-Item $src $SkillRoot -Recurse -Force
}
Write-Host "V2.3 files installed. Existing same-name files were backed up to $Backup" -ForegroundColor Green
Write-Host "V2.2 versioned scripts remain untouched." -ForegroundColor Yellow
