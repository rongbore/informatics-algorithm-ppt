param(
    [string]$SkillRoot = "D:\Codex\skills\interactive-lesson-video-builder"
)

$ErrorActionPreference = "Stop"
$SourceRoot = $PSScriptRoot

if (!(Test-Path $SkillRoot)) {
    New-Item -ItemType Directory -Force -Path $SkillRoot | Out-Null
}

$BackupRoot = Join-Path (Split-Path -Parent $SkillRoot) (
    (Split-Path -Leaf $SkillRoot) + "_backup_v2_4_" + (Get-Date -Format "yyyyMMdd_HHmmss")
)
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

Get-ChildItem -LiteralPath $SkillRoot -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $BackupRoot -Recurse -Force
}

Get-ChildItem -LiteralPath $SourceRoot -Force |
    Where-Object { $_.Name -notin @("install_v2_4.ps1", ".git") } |
    ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $SkillRoot -Recurse -Force
    }

Write-Host "V2.4.1 Skill installed to: $SkillRoot" -ForegroundColor Green
Write-Host "Previous Skill backup: $BackupRoot"
Write-Host "Next: python -m pip install -r requirements-v2.4.txt"
