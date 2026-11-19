param(
    [string]$Target = 'D:\Codex\skills\cpp-lesson-pdf'
)
$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $source 'SKILL.md'))) {
    throw 'Cannot locate SKILL.md. Run this script from the extracted cpp-lesson-pdf package.'
}
if (Test-Path $Target) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = "$Target.backup-$stamp"
    Copy-Item -Path $Target -Destination $backup -Recurse -Force
    Write-Host "Backed up existing Skill: $backup"
}
New-Item -ItemType Directory -Force -Path $Target | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $Target -Recurse -Force
if (-not (Test-Path (Join-Path $Target 'SKILL.md'))) {
    throw 'Installation verification failed: missing SKILL.md'
}
Write-Host "Installed cpp-lesson-pdf Skill to $Target"
