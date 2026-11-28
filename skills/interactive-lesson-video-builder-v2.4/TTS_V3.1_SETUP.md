# V3.1 TTS setup (Tencent Cloud first, local offline fallback)

## 1. Install optional TTS packages

From the Skill directory:

```powershell
python -m pip install -r requirements-v3.1-tts.txt
```

## 2. Prepare local offline Mandarin fallback first

The V3.1 fallback uses sherpa-onnx VITS and a Mandarin AISHELL-3 model package. Download/extract it:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local_tts_v31.ps1 -ModelRoot D:\AIModels\sherpa-onnx-vits-zh-aishell3
```

Then set the paths printed by the script (replace with the actual paths printed on your machine):

```powershell
$env:SHERPA_TTS_MODEL = "D:\AIModels\sherpa-onnx-vits-zh-aishell3\vits-icefall-zh-aishell3\model.onnx"
$env:SHERPA_TTS_TOKENS = "D:\AIModels\sherpa-onnx-vits-zh-aishell3\vits-icefall-zh-aishell3\tokens.txt"
$env:SHERPA_TTS_LEXICON = "D:\AIModels\sherpa-onnx-vits-zh-aishell3\vits-icefall-zh-aishell3\lexicon.txt"
$env:SHERPA_TTS_RULE_FSTS = "D:\AIModels\sherpa-onnx-vits-zh-aishell3\vits-icefall-zh-aishell3\phone.fst,D:\AIModels\sherpa-onnx-vits-zh-aishell3\vits-icefall-zh-aishell3\date.fst,D:\AIModels\sherpa-onnx-vits-zh-aishell3\vits-icefall-zh-aishell3\number.fst"
$env:SHERPA_TTS_SPEAKER_ID = "21"
```

Review the upstream model and dataset license before redistribution or commercial use. The model is not bundled in this repository.

## 3. Optional Tencent Cloud free-tier setup

A parent/guardian or account administrator should manage the cloud account, credentials and billing settings. Do not bypass identity checks or billing controls.

Tencent's free TextToVoice package must be explicitly claimed in the Tencent console. The free resource packages are voice-category-specific, valid for three months after claiming, and apply to the general TextToVoice interface rather than long-text synthesis. Check the current remaining free characters and confirm postpaid billing is disabled in the console before enabling this adapter.

Only after that console verification, set these values in the local process:

```powershell
$env:TENCENTCLOUD_SECRET_ID = "configured locally by account administrator"
$env:TENCENTCLOUD_SECRET_KEY = "configured locally by account administrator"
$env:TENCENT_TTS_REGION = "ap-guangzhou"
$env:TENCENT_TTS_ALLOW_FREE_TIER = "true"
$env:TENCENT_TTS_POSTPAID_DISABLED = "true"
$env:TENCENT_TTS_FREE_BUDGET_CHARS = "YOUR_VERIFIED_REMAINING_FREE_CHARACTERS"
```

The budget value must be no greater than the free quota currently remaining in the console. It is a Skill-side cap, not a live Tencent quota query. The persistent ledger tracks this Skill's reserved characters at:

`%USERPROFILE%\.lesson-video-builder\tencent_tts_budget_v31.json`

If the account's free quota is shared with other applications, reduce the configured cap to account for their use. Never set the cap to a value larger than the verified free balance. If any required setting is absent, V3.1 blocks cloud requests and selects local TTS.

The `TENCENT_TTS_POSTPAID_DISABLED=true` variable is an explicit operator acknowledgement only; it does not change Tencent billing settings. If postpaid billing cannot be confirmed disabled in the console, leave Tencent disabled and use local mode.

## 4. Run

Tencent-first with automatic local fallback:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_video_builder_v2_6.ps1 -Phase Prepare -Pptx .\input\lesson.pptx -OutputDir .\output\lesson -NarrationJson .\output\lesson\narration_events.json -TtsProvider tencent
```

Force local-only synthesis:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_video_builder_v2_6.ps1 -Phase Prepare -Pptx .\input\lesson.pptx -OutputDir .\output\lesson -NarrationJson .\output\lesson\narration_events.json -TtsProvider local
```

The user-facing workflow remains one PPTX upload; narration JSON is an internal Skill artifact. For a full Render phase, continue with the same output directory and the internally generated verified alignment/storyboard files.

## 5. Safety behavior

- No cloud credentials, no verified free budget, no explicit free-tier opt-in, or no postpaid-disabled acknowledgement => no Tencent API call.
- Character reservations are written before each Tencent API call and are not refunded after ambiguous failures.
- No automatic cloud retries, no automatic resource purchases, no automatic pay-as-you-go activation.
- Cloud API failure or budget exhaustion => local offline fallback.
- Missing local model => stop and report INCOMPLETE; never switch silently to Azure or Edge.
- Machine QA always leaves `manual_review_required=true` and `auto_approved=false`.
