# Windows + Codex installation

## Requirements
Windows PowerShell, Git (optional), Python 3.10+, Node.js 20+ and npm. Check `python --version`, `node --version`, `npm --version`.

## Local installation
Unzip to `D:\algorithm-skills\informatics-algorithm-ppt` (project source). For a local Codex Skill, copy the complete folder to the **actual** Codex skill search path. Common local path is `%USERPROFILE%\.agents\skills\informatics-algorithm-ppt` (check your Codex version's documentation); the directory must contain `SKILL.md` at its root. If you want to keep source on D:, use a Windows directory junction or a copy; avoid assuming the cloud Codex environment can access your D: drive.

PowerShell example:
```powershell
$src = 'D:\algorithm-skills\informatics-algorithm-ppt'
$dst = Join-Path $HOME '.agents\skills\informatics-algorithm-ppt'
New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
Copy-Item $src $dst -Recurse -Force
Test-Path (Join-Path $dst 'SKILL.md')
```

## Demo and tests
```powershell
cd D:\algorithm-skills\informatics-algorithm-ppt
python scripts/generate_demo_trace.py
python -m unittest discover -s tests -v
python scripts/validate_trace.py examples/sliding-window/trace.json
cd templates/slidev
npm install
npm run dev
npm run build
```

Open the development URL printed by Slidev. Test Next, Previous, Reset and keyboard navigation. `npm run build` writes static output to `dist`.

## Troubleshooting
- `node` not found: install Node.js LTS and reopen terminal.
- `python` not found: check Python launcher (`py -3`) or PATH.
- Skill not detected: verify root `SKILL.md`, exact directory, supported skill search path and restart Codex session.
- PowerShell execution policy: use `npm.cmd` rather than changing system-wide execution policy.
- Port busy: use `npm run dev -- --port 3031`.
- Browser blank: inspect browser console and `npm run build` errors; don't claim successful export.
- Web Codex: cloud workspace does not directly mount local `D:`. Upload repository or push to GitHub and install in the supported cloud environment.
