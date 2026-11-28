---
name: interactive-lesson-video-builder.v2.4
version: 2.4.1-alpha.6
description: Source-audited media engine for PowerPoint visual regions, phrase-level narration, measured timing, rendering and QA; orchestrated by V2.6 single-upload workflow.
---

# Interactive Lesson Video Builder V2.4 Engine

V2.4 is the deterministic execution engine used by the active V2.6 Skill. V2.2 and V2.3 remain preserved for compatibility.

## V2.6 orchestration entrypoint

The active Skill invokes `scripts/run_video_builder_v2_6.ps1` to coordinate the deterministic stages. The runner's Prepare and Render phases are internal to the Skill's single user request; the user does not create intermediate assets.

## Engine workflow

1. Export every slide preview from PowerPoint using `scripts/render_slides_v2_4.ps1`.
2. Extract native text boxes and table-cell geometry using `scripts/extract_slide_regions_v2_4.py`.
3. Add image-only visual regions only from hash-bound vision proposals with an independent verification pass.
4. The Skill agent authors narration events and storyboard from the PPTX and speaker notes; the user does not prepare intermediate JSON.
5. Generate per-phrase TTS and measured timings using `scripts/generate_audio_v2_4.py`.
6. Prepare exact machine-hashed context using `scripts/prepare_alignment_inputs_v2_4.py`.
7. Run the alignment planner and independent verifier as separate passes.
8. Finalize and compile using `scripts/finalize_alignment_plan_v2_4.py` and `scripts/compile_alignment_v2_4.py`.
9. Render using `scripts/render_lesson_v2_4.py` from the compiled report only.
10. Validate media using `scripts/validate_full_video_v2_4.py`.

## Three-way alignment contract

Every rendered focus overlay must link:
- Visual: exact PPTX and slide-image hashes, slide number, stable region ID, normalized bbox, geometry source and verification status.
- Speech: narration event ID, phrase index, exact phrase and TTS audio hash.
- Time: actual measured start/end interval, timing JSON hash and FFprobe-probed duration.

Subtitles and focus overlays derive from the same measured phrase interval. All identifiers and hashes must agree.

## Automatic full-course behavior

- Generate a representative pilot internally using slides selected from the actual deck, not fixed slide numbers.
- Run deterministic pilot checks automatically; do not pause for user approval before the full draft render.
- If deterministic pilot checks pass, render every slide automatically.
- A low-confidence or ambiguous focus mapping is omitted while the original slide and narration remain in the full video; log it for review.
- A failed slide render/TTS operation is retried. If still unsuccessful, mark the package incomplete and do not claim a full video.
- Human semantic review remains required after generation; it is a quality sign-off, not a prerequisite to create the draft.

## Matching, timing and animation policy

- Native PPTX geometry is preferred; all slide previews are hash-bound.
- Vision geometry and phrase mapping require confidence >= 0.90 and independent verification.
- Low-confidence, ambiguous, stale or unverified mappings are not rendered.
- Timing is phrase-level, not word-level or phoneme-level forced alignment.
- Never infer time from slide duration, character count, reading speed or guessed timestamps.
- Algorithm-state animation requires a source-grounded state trace with validated initial state, every operation, before/after state, invariants and final state. A focus rectangle is not a data-structure simulation.
- If a valid state trace cannot be built, retain the original slide and narration; do not fabricate animation.

## QA and release

- Recompute slide-image, audio and timing-file SHA-256 values immediately before rendering.
- Check source fingerprints, phrase coverage, interval overlap, geometry bounds, subtitle intervals, focus ownership, stream metadata, full decode and audio/video duration alignment.
- Always report `manual_review_required=true` and `auto_approved=false`. Machine QA does not certify teaching correctness.


## V3.0 extension

The active single-upload Skill now supports Azure AI Speech and a source-specific DSU animation profile. The V2.4 alignment contract remains authoritative: audio timing is measured with FFprobe; state frames are hash-bound to the source PPTX; each animation cue has a stable event ID; no guessed phrase timing is allowed. Azure mode requires `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`. The runner must not silently fall back to Edge/eSpeak. For a detected four-exercise DSU deck, build and validate the four animation chapters, synthesize the matching cue narration, render frames for measured intervals, insert the chapters after their exercise sections, and rebuild the SRT with the same offsets. Output remains 1920×1080 at 30 FPS. Human review remains mandatory.


### Source-deck fidelity correction (V3.0.1)
The DSU animation narration is grounded in the uploaded 34-slide deck. The food-chain chapter must use slide 25's n=5 result (A={1,2,3,5}, B={4}, A eats B; three statements consistent; false count 0) and slide 26's n=3/two-statement variation (replace first statement with 2 1 4; index 4 is out of range; false count 1). Do not invent example statements such as 1 eats 2 / 2 eats 3 / 3 eats 1. Distinguish the Galaxy queue offset of ship 2 (4, zero-based) from the separate path-compression teaching example 2→3→4 (edge weights 1+1=2). Animation cue IDs must match renderer IDs exactly. Azure timing stores one event-level interval per state frame plus nested phrase-level intervals; subtitles use the measured phrase intervals.


## V3.1 Tencent-first / local-offline TTS architecture

The default provider is Tencent Cloud's general `TextToVoice` API, with a fully offline Mandarin sherpa-onnx VITS engine as the fallback. Azure and Edge remain explicit legacy options only; they are not selected by default.

### Zero-unauthorized-charge policy (mandatory)
- Tencent Cloud synthesis is disabled unless all of the following are explicitly configured: `TENCENT_TTS_ALLOW_FREE_TIER=true`, `TENCENT_TTS_POSTPAID_DISABLED=true`, valid Tencent credentials, and `TENCENT_TTS_FREE_BUDGET_CHARS` greater than zero.
- The configured character cap must be no greater than the remaining free quota shown in the Tencent console. The operator must verify that postpaid billing is disabled in the Tencent console; the environment acknowledgement is not a substitute for that console check.
- A persistent local ledger reserves characters before each API request. It is conservative: reservations are not refunded after uncertain network failures. Cached phrases are reused without another API request. No automatic cloud retries are performed.
- If preflight fails, the configured free-tier cap is reached, or the cloud request fails, the router switches to local sherpa-onnx. It never enables pay-as-you-go, buys a resource pack, or silently switches to another paid provider.
- If local model files are unavailable, the run stops as INCOMPLETE; no Edge/Azure fallback is attempted.
- Do not put Tencent SecretId/SecretKey in source control, narration JSON, logs or chat.

### Tencent Cloud provider
- Use the general `TextToVoice` endpoint only; do not use long-text synthesis or podcast endpoints for the free-tier path.
- API requests are split to at most 140 characters (below Tencent's documented 150 Chinese-character request limit).
- Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`; optional region/voice controls are in `tts_v31.env.example`.
- The Tencent SDK is optional and imported only when a guarded cloud request is made. Install `requirements-v3.1-tts.txt` for the cloud and local providers.

### Local offline provider
- Engine: sherpa-onnx VITS, using the public Mandarin AISHELL-3 multi-speaker model package as one supported model option.
- Install the model with `scripts/setup_local_tts_v31.ps1`, review the upstream model license, then set `SHERPA_TTS_MODEL`, `SHERPA_TTS_TOKENS`, and optional lexicon/rule paths.
- Local inference uses CPU and does not send narration to a cloud service. The model must be downloaded before offline synthesis can run.

### Runner
- `-TtsProvider tencent` is the default. It uses Tencent only when all free-tier guards pass; otherwise it uses local sherpa-onnx.
- `-TtsProvider local` forces offline generation.
- `-TtsProvider edge` and `-TtsProvider azure` are retained as explicit legacy selections, not defaults.
- Course narration and source-grounded DSU animation narration use the same selected V3.1 provider and measured phrase-timing pipeline.
- Every run reports requested provider, actual providers, fallback events, character reservations, timing and QA. Human listening review remains required; `auto_approved=false`.
