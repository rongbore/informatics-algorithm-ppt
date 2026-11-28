---
name: interactive-lesson-video-builder
version: 3.0.0-beta.1
description: Single-upload, full-course AI teaching-video production. Automatically inspects PPTX, writes narration, plans scenes, synthesizes speech, aligns verified visual regions to measured audio time, renders MP4 and reports QA.
---

# Interactive Lesson Video Builder — Active Skill

Use the V2.4.1 source-audited media engine, V2.6 single-upload orchestration contract and V3.0 Azure voice + algorithm-animation extensions. V2.2/V2.3 compatibility assets remain preserved and must never be overwritten.

## One-upload user contract

**Required user input: one classroom PPTX file.** When a PPTX is uploaded and the user asks for a teaching video, start the complete workflow immediately. Do not ask the user to create or upload narration JSON, slide images, region manifests, storyboards, TTS files, subtitles, timing files, or command sequences.

Use these defaults unless the user explicitly overrides them:
- Language: Simplified Chinese when the source is Chinese; otherwise follow the source language.
- Audience: middle-school informatics/algorithm learners when the deck is an informatics lesson; infer other audiences from the deck.
- Teaching voice: Azure AI Speech `zh-CN-YunjianNeural`, default `sports-commentary-excited`; audition `sports-commentary` as the balanced A/B profile.
- TTS provider: Azure AI Speech; do not silently fall back to Edge/eSpeak when Azure is selected.
- Video output: 1920×1080 at 30 FPS unless the source or user explicitly requires otherwise.
- Preserve original slide order, terminology, facts, examples, formulas, code, diagrams, constraints and teacher notes.
- Output: full-course MP4, SRT, narration script, storyboard, measured timeline, source/alignment audit, QA report and a ZIP production package.
- Preserve source aspect ratio; use 1080p output where practical.
- Do not add background music by default. Never let decorative audio obscure instruction.

Ask a question only if the PPTX cannot be opened or a truly blocking preference cannot be inferred. Otherwise proceed with defaults.

## Executable production workflow

The active Skill must invoke `scripts/run_video_builder_v2_6.ps1` in the V2.4 engine directory with `-TtsProvider azure -AzureVoiceProfile coach_excited`. The user still supplies only the PPTX; narration JSON, verified alignment decisions and storyboard JSON are authored internally by the Skill agent and stored in the run workspace. Azure credentials are configured in the local environment or GitHub Actions Secrets (`AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`; optional `AZURE_SPEECH_ENDPOINT`). Never put keys in source files, prompts, chat messages or commits. If credentials are missing, stop the Azure audio stages and mark the run INCOMPLETE; do not substitute a different provider.

1. Create a unique run workspace for the uploaded PPTX.
2. Inspect the complete deck and write the narration event JSON using `prompts/lesson_narration_compiler_v2_4.md`.
3. Invoke the runner with `-Phase Prepare`, the PPTX, workspace and agent-authored narration JSON. This exports slides, extracts native regions, generates TTS and measured timing, and prepares the machine-hashed alignment context.
4. Read the alignment context and matching slide previews. Use the alignment planner and independent verifier prompts to create the verified alignment decisions JSON. Use `prompts/storyboard_compiler_v2_6.md` to author the storyboard JSON. The user must not be asked to prepare these files.
5. Invoke the runner with `-Phase Render`, the same PPTX/workspace, and the internally generated decisions/storyboard, retaining `-TtsProvider azure -AzureVoiceProfile coach_excited`. It finalizes and compiles alignment, renders and validates an internal representative pilot, then renders and validates the full course.
6. For a source-verified four-exercise DSU deck, run `detect_dsu_deck_v30.py`, `build_dsu_v30_animations.py`, synthesize each animation narration cue with Azure, render one state frame per measured cue using `render_dsu_animation_chapters_v30.py`, and insert the four narrated chapters after their matching exercise sections with `compose_full_course_v30.py`. Rebuild the SRT using the same insertion offsets. Do not run the DSU profile on a generic or mismatched deck.
7. Package the final 1080p MP4, synchronized SRT, four animation chapters, editable frame assets, voice profiles, narration, storyboard, measured timing, source audit and QA report.
8. Verify that the delivery manifest says `status=COMPLETE`, the final MP4 and ZIP exist, the full validation report exists, and the subtitle duration matches the final video before presenting download links. If any required stage fails, report `INCOMPLETE` and deliver diagnostics only; never claim completion.

The two runner phases are internal orchestration steps, not separate user tasks. The Skill agent must carry them through in one request.

## Fully automatic end-to-end workflow

The agent orchestrates semantic authoring and independent review; the deterministic engine handles extraction, audio timing, hashes, compilation, rendering and media QA.

1. **Discover and inspect input:** identify the uploaded PPTX, create a per-run output folder, inventory slide count, dimensions, notes, text, code, formulas, tables, diagrams, exercises and source language. Hash the original source. Never edit the original PPTX.
2. **Render every slide:** use PowerPoint COM on Windows for source-faithful PNG export. Verify exported count, order, dimensions and per-slide SHA-256. If PowerPoint is unavailable, report the missing prerequisite; do not silently substitute a layout-changing converter and claim fidelity.
3. **Extract visual regions:** run the native PPTX extractor for text boxes and table cells. Add image-only regions from slide previews through the visual-region prompt. Bind all regions to exact slide-image hashes. Stable region IDs are generated by the extractor, never invented by the model.
4. **Author the complete lesson narration:** the Skill agent creates narration events from source slide content and speaker notes using `prompts/lesson_narration_compiler_v2_4.md`. It creates event IDs and phrase order, preserves exact identifiers/formulas/values, explains code in execution order, and adds thinking prompts only where pedagogically supported. It writes the JSON itself.
5. **Create a complete storyboard:** classify each slide/section as concept, diagram, code, worked example, exercise, recap or transition. Specify shot type, framing, pan/zoom, visual target IDs, transition, narration event IDs and timing dependency. Do not invent camera movement where it would impair reading.
6. **Synthesize speech:** generate each narration phrase using the configured Chinese neural TTS voice. Measure actual phrase durations with FFprobe. Retry transient failures. Save per-slide audio and timing JSON. Never infer timestamps from character count, slide duration or guessed speech rate.
7. **Prepare machine-grounded alignment context:** run `prepare_alignment_inputs_v2_4.py`; all cryptographic hashes are computed by code, never by the model.
8. **Plan and independently verify alignment:** the planner maps each phrase to zero, one or multiple exact region IDs. A distinct verifier checks the source quote, slide, geometry, phrase identity and semantic correspondence. Require confidence >= 0.90 for focus overlays. Preserve rejected candidates and reasons.
9. **Compile:** run the finalizer and compiler. Only verified region/phrase/time records with matching source, image, audio and timing fingerprints can produce focus overlays. Unmatched transition phrases are valid. Ambiguous mappings remain unfocused and are listed for review; they do not block otherwise valid full-course rendering.
10. **Automatic internal pilot:** before the full render, render a representative sample selected dynamically from the actual deck (opening, concept, code/formula, worked example, exercise/recap where available). Run machine QA and inspect sampled frames for bounds, missing assets, subtitle collision and media integrity. This is an internal gate, not a user approval step. If the pilot has a deterministic technical failure, repair/retry automatically; if unresolved, stop with a diagnostic package.
11. **Render the entire deck automatically:** after the internal pilot passes deterministic checks, render all slides without waiting for user confirmation. Generate subtitles and focus overlays from the compiled alignment report only. Use measured phrase intervals; suppress subtitles during thinking pauses. Preserve original slide order and aspect ratio.
12. **Algorithm animation:** create dynamic algorithm scenes only when a source-grounded, machine-readable state trace is available and independently validated. A trace must include initial state, every operation, state before/after, invariants and final state. Validate each transition against the supplied code/problem semantics. If a valid trace cannot be established, use the original slide plus verified focus/zoom; never fabricate node, array, DP or graph states.
13. **Full media QA:** verify video/audio streams, full decode, slide coverage/order, duration, timing coverage/non-overlap, subtitle intervals, pause suppression, focus ownership, geometry bounds, source hashes and audio-video duration consistency. Generate a machine-readable report and a human review checklist.
14. **Package and deliver:** provide the MP4 and one ZIP containing all production assets. Also provide standalone narration, storyboard, SRT, timeline, alignment audit and QA report. Report all limitations and unresolved slides.

## Three-way alignment contract

Every visible focus event links all three sources:
- **Visual:** PPTX SHA-256, slide-image SHA-256, slide number, stable region ID, normalized bbox, geometry source and independent verification status.
- **Speech:** narration event ID, phrase index, exact phrase, source slide and TTS audio SHA-256.
- **Time:** actual measured start/end seconds, timing JSON SHA-256 and FFprobe duration.

All identifiers and fingerprints must agree. Subtitles and focus overlays derive from the same measured phrase interval. Renderer input is the compiled report, never a freehand timeline.

## Reliability and fallback policy

- No guessed timestamps, slide-duration ratios, character-count timing, nearest-text fallback or unverified fuzzy matches.
- No stale source/audio/timing/slide-image hashes.
- No focus overlay for ambiguous, unsupported or confidence-below-0.90 geometry.
- A failed visual mapping degrades only that phrase to the original unhighlighted slide; it must not invent a focus target.
- A failed algorithm-state trace degrades to the source slide and narration, with the animation marked unavailable.
- Retry transient TTS/render failures with bounded retries. Never silently omit a slide.
- If a slide cannot be narrated or rendered after retries, stop final release and deliver diagnostics/partial artifacts clearly marked INCOMPLETE; do not label it a complete video.
- Machine QA passing does not prove instructional correctness. Always set `manual_review_required=true` and `auto_approved=false`, but do not require the user to approve a pilot before generating the full draft.

## Output package

At minimum produce:
- source manifest and slide previews;
- native/verified visual-region manifest;
- narration event JSON and readable narration document;
- storyboard JSON/CSV;
- per-phrase audio and measured timing JSON;
- alignment context, planner decisions, independent verification, finalized plan and compiled alignment report;
- full-course MP4 and SRT subtitles;
- alignment audit, QA report and unresolved-item/review checklist;
- ZIP containing all deliverables.

## Runtime prerequisites and truthful status

The Skill must check prerequisites at run start: Python 3.10+, PowerPoint on Windows for source-faithful export, FFmpeg/FFprobe, required Python packages, TTS network availability and sufficient disk space. Explain any missing prerequisite with the exact remediation. Do not claim a stage ran unless its output and validation exist.

## Version isolation

V2.2 and V2.3 scripts, outputs, caches and historical artifacts remain intact. V2.4 remains the source-audited engine. V2.6 changes the user workflow to single-upload, full-course automatic production without weakening the engine's integrity checks.


## V3.0 Azure coach voice and DSU animation extension

### Azure voice audition
- Use Azure AI Speech voice `zh-CN-YunjianNeural`.
- Produce two audition profiles from the same source passage: `coach_excited` = `sports-commentary-excited`; `coach_balanced` = `sports-commentary`.
- These are two expression profiles of the same Azure voice, not two vendors. Save SSML, MP3, hashes and FFprobe durations. A human listener must select the preferred profile; machine QA cannot grade coach-like expression.
- Preserve technical terminology and numbers. Use phrase-level synthesis, punctuation pauses, measured audio timing and bounded retries.
- Azure bills synthesized text characters; report estimated/actual usage and never start an unbounded retry loop.

### Source-grounded DSU animation
- Detect the four-exercise DSU source by slide count and section headings before invoking the specialized renderer.
- Render the four source sections: relatives (slides 13–15), fencing (16–21), food chain (22–27), and Galaxy (28–33).
- The animation event narration is stored in `prompts/dsu_animation_narration_v30.json`. Event IDs and order must match the rendered state-frame manifest.
- Ordinary DSU, three-slot S/P/E food-chain DSU, and weighted queue DSU are distinct models. Never substitute one model's state transitions for another.
- For the food-chain example, preserve the deck's three-slot relations: for x eats y, merge P(x)=S(y), S(x)=E(y), E(x)=P(y). Reject self-eating, out-of-range IDs and contradictions.
- For the Galaxy example, preserve the directed append operation and the receiving team's old size as the new root-edge offset. Weighted path compression must accumulate old edge offsets before rewriting parents.
- Every state frame is hash-bound to the source deck and matched to exactly one Azure narration cue. Its display interval comes from the measured speech event and following pause, not a guessed duration.
- Insert animation chapters after slides 15, 21, 27 and 33; rebuild SRT timestamps with the same insertion durations.
- Require 1920×1080, 30 FPS, audio/video duration checks, full decode and source/state hash verification. Keep `manual_review_required=true` and `auto_approved=false`.

### Azure configuration and fallback
- Required environment: `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`; optional custom endpoint `AZURE_SPEECH_ENDPOINT`.
- Never commit secrets or ask the user to paste a key into chat. Recommend local environment variables or GitHub Actions Secrets.
- If Azure is unavailable, the algorithm visual chapters may be generated without narration as a preview, but the final narrated course is INCOMPLETE. Do not silently fall back to Edge TTS or eSpeak.
- The two voice profiles are A/B candidates; do not call them approved until a human listens to both.


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
