# Dance lab: choreography, motion and personal taste

User direction: an ambitious Harness²/ChatGPT project for compelling dance, with local-model planning/staging and GPU execution. Many dance styles and subjective taste matter. Repeatedly finding source clips should not be the main workflow. This is a proposed project, not a working dance generator.

## Useful end state

Give the system a track or beat structure, a character/rig, a mood and a few preferences. Receive several short, visibly distinct dance phrases with synchronized previews. Choose appealing moments or explain what feels wrong; revise those spans without losing the good parts. Later assemble longer choreography with variation, buildup and resolution. Keep personal preference separate from physical correctness and genre conventions.

ChatGPT/Sol can serve as interactive choreographic director and help turn informal feedback into experiments. A local model can select and sequence motion phrases, manage constraints and stage jobs. A motion generator/retargeter and renderer do GPU work. Harness² is an offline optimizer of the planning/tool workflow between auditions; it should not be responsible for every frame or asked to learn personal taste solely from model-judge scores.

## Representation: score plus executable motion

A symbolic score describes timing and intent; it is not evidence that a body can perform the dance. Every executable move references an actual tested motion asset or a motion-generator job that has returned valid output.

Each motion phrase carries:
- Asset/version and provenance; rig/retargeting compatibility.
- Duration in beats, tempo range and permissible time scaling.
- Entry/exit stance, supporting foot, heading and root position/velocity.
- Contact events, turning/travel envelope and required floor space.
- Energy, amplitude, rhythm accents, body-part emphasis and stylistic tags.
- Transition compatibility and known visual limitations.

Tags support search; they do not establish stylistic authenticity. Learn what tags are useful through auditions rather than assuming a universal dance taxonomy. Cultural traditions and attribution belong in provenance, with uncertainty retained.

A scene score adds phrase IDs, beat offsets, intensity, facing, floor path, transition IDs, optional mirroring and camera cues. The compiler resolves these into rig motion. Mirroring is only allowed if contacts/handedness and partner constraints remain valid. Root motion and joint motion need consistent coordinates; no teleporting between phrases.

## Working without constant source hunting

1. Start with a small, reusable set of licensed/owned motion phrases or procedurally authored rig motions. Qualify quality and compatibility once.
2. Add text-conditioned motion generation if a chosen tool supports the actual rig/output contract. Preserve its generated artifacts and provenance; do not assume text-to-motion alone produces polished choreography.
3. Retrieve from that library by entry/exit state and musical intent. Request new material only for a specific missing capability, such as a turn ending on the left foot.
4. Keep accepted generated phrases and transitions, so each round improves the reusable collection rather than returning to a blank search page.
5. Make external reference search optional: a user may supply a clip or name a tradition, but ordinary auditions should run from a brief and the existing library.

No motion backend, dataset license, trained weights or GPU recipe is selected by this note. Verify primary documentation, licensing and artifacts when choosing one. Do not present generated approximations as faithful examples of a named dance tradition without review.

## Two independent evaluation layers

**Execution checks:** valid skeleton, finite joint data, joint-limit compliance, foot-contact plausibility, sliding, self/partner collisions, root continuity, balance proxies, beat timing, duration and decoded rendered output. Balance proxies and contact heuristics are screening signals, not proof of biomechanical feasibility. Stylized/anime constraints may deliberately differ from human biomechanics; declare them before judging.

**Taste review:** groove, phrasing, musicality, anticipation/release, expressive clarity, surprise, coherence, appropriate repetition and character fit. Let the user choose which qualities matter for a given song. A clean physical score can still be boring. A compelling stylized move may violate a generic realism metric. Camera/editing can conceal motion defects or manufacture excitement, so first compare a fixed camera and later judge cinematography separately.

Use short blind A/B auditions, with “both”, “neither” and timestamped keep/change regions. Ask sparse questions that change the next candidate. Keep absolute rejection reasons separate from relative preference. Do not train one scalar “good dance” score from unrelated genres, moods and characters.

## First experiment ladder

| Stage | Deliverable | What would count as evidence |
|---|---|---|
| D0 | Synthetic 8-beat phrase score from a tiny atlas | Semantic intent, entry/exit contacts and timing pass host checks; no claim of dancing |
| D1 | Same score executed on one neutral rig | Decoded joint tracks and fixed-camera preview; inspect continuity |
| D2 | Three 8–16beat variants using identical assets | Visible variation in rhythm/energy/order; human ranking |
| D3 | Revise one disliked span | Preserve accepted neighboring motion and beat alignment |
| D4 | Add a new generated phrase | Actual output fits rig/contact/transition contract and improves options |
| D5 | 32beat sequence with motif and variation | Human phrase-level coherence; track cumulative drift/repetition |
| D6 | Retarget accepted choreography to anime avatar | Contact, proportions and expressiveness survive; original retained |
| D7 | Export scene/reference pack for H3 | Verify H3's real accepted interface; compare motion fidelity after generation |
| D8 | Duet/partner choreography | Shared timing, spacing, contact and collision checks; higher-risk complexity |

Start with no music upload: explicit beat times/BPM and synthetic rhythm suffice for contract tests. When using actual music, distinguish onset/beat/downbeat/phrase detection confidence and allow correction. A BPM number alone is not musical phrasing; tempo drift and syncopation must be represented.

## What the learning harness can change

Allowed adaptations: planning prompt, compact phrase descriptors, retrieval ranking, candidate breadth, transition-selection guidance, error-feedback format and retry allocation. Track all versions and compute costs.

Host-owned and frozen during comparison: source motion, rig definition, safety/continuity thresholds, musical timeline, held-out clips, completed artifact receipts and user feedback labels. A model cannot improve its score by weakening foot-sliding detection or redefining the desired beat.

Compare: fixed planner; one constrained correction; adapted planner; later tuned model with fixed harness; tuned model plus adapted harness. Use the same motion backend and candidate budget first. If both planner and generator change, label the joint intervention rather than attributing gains to Harness² alone.

Do not overfit to a single preferred sequence. Hold out songs/rhythmic patterns, phrase families, rigs and preference sessions. Retest previous favorites for regression while allowing taste to depend on context. A user-approved sequence can seed training only with explicit provenance and appropriate permission.

## Efficient model allocation

- Tiny/small model: retrieve legal next phrase, choose bounded intensity/facing, reject incompatible move, route feedback to a span.
- Compact MoE: plan an8–32beat sequence, create controlled alternatives, manage jobs and repair a transition.
- Dense model/ChatGPT: interpret expressive direction, identify why a sequence feels flat, propose motif/buildup structure and help formulate comparative auditions.
- GPU motion system: generate/retarget/blend/render. Its useful output rate and failure cost matter more than language-model tokens/s.
- Deterministic runtime: timing, pose interpolation, leases, rendering dispatch and output checks.

## Cheap first batch and stop rules

Prepare D0 without model calls; include failed transitions, impossible tempo scaling and malformed move IDs. Then a small matched planner batch with held-out move names and rhythms. Advance to D1 only after a real backend/asset/rig contract is verified. Use thumbnails/low-resolution fixed-camera previews before expensive final rendering. Cache unchanged motion and rerender only the edited span plus transition margins.

Cap proposals, generated seconds, render resolution, retries and wall time separately. Stop a round if variants are physically invalid, near-duplicates or insufficiently distinct for useful preference feedback. Report those failures instead of asking the user to rank noise. No rented GPU is needed for the initial symbolic tests; obtain a current finite budget before GPU generation/training.

Success is not “the model wrote a dance plan.” It is a sequence the user finds compelling, with reusable motion and a cheaper/more reliable path to the next good sequence.

## D0 receipt (2026-10-19)

Implemented `harness2/dance_score.py`, with three passing test methods and six saved cases in `evidence/dance-score-offline.json`. One compatible eight-beat score compiles to four seconds at 120 BPM. Five invalid proposals are rejected: transition order, tempo, unknown move, short duration and unresolved final stance. The compiler also rejects stale atlas revisions, malformed fields and non-finite tempo. No provider calls or GPU work.

These are synthetic boundary labels, not actual contacts, joint tracks or licensed motion assets. Equality of declared entry/exit labels cannot establish smooth blending, balance, root continuity or attractive choreography. This deliberately tiny atlas has only one useful complete phrase: it tests the contract, not creative diversity. Before a model comparison, expand alternatives and freeze renamed held-out atlases; before an audition, bind descriptors to verified motion and inspect fixed-camera renders.

Next concrete gate: qualify a minimal rig plus several reusable motion phrases, then compare short variants with identical assets and timing. Store keep/change spans and both/neither preferences separately from execution failures. An affordable planner can stage these auditions; a model judge must not stand in for the user's taste.

## Local renderer bridge found (2026-10-19)

Existing Hermes assets include an isolated Blender 4.5.3 runtime under `runs/blender-runtime/Blender.app` and procedural scenes under `runs/round4/` in `/Users/adom/Development/hermes-testing`. Source `tools/avatar_backend.py` creates a procedural character with head/arm pivots but static leg geometry; this is not yet a dance rig. `tools/blender_mcp.py` supports neutral/wave/nod/point, two-second scenes and three reference frames. Those tools cannot execute D0 dance phrases without new rig/motion work. Reuse the runtime and camera/material setup; do not mistake static legs or a translated root for verified foot-contact choreography. No new render was performed during this inspection.

## First executable procedural motion (2026-10-19)

Luna implemented `harness2/dance_motion.py`: restrained/broad generic step-touch-like variants, eight beats at 120 BPM, 81 samples including endpoint over four seconds. World-space joints use two-link inverse kinematics and authored support/swing tracks. The host validator checks finite positions, exact timestamps, supporting contacts, contact height, segment lengths, planted-ankle sliding and a 0.20 m/sample continuity bound. Five targeted tests reject corrupt tracks and inspect beat boundaries. These are screening checks, not balance, joint-limit, collision or biomechanical proof.

Parent rendered both variants side by side with an inexpensive Blender Workbench scene: cyan restrained, orange broad. Output is 40 frames at 10fps, 512x320, four seconds; generation/validation/render/encoding took 4.25 seconds. Sparse decoded frames confirmed visible rigs, changing poses and modest amplitude differences. No full-motion human taste review has occurred.

Media: `/Users/adom/Development/hermes-testing/runs/harness2-dance-motion-v2/comparison.mp4`. Joint tracks: sibling `tracks.json`. Evidence: `dance-motion-render-v2.json`. First render failed because the renderer expected bone_edges nested under metadata; original failed receipt and log remain, and corrected v2 retained the identical track hash.

This is an alternative first executable prototype, not full completion of D1: it does not execute the old D0 symbolic atlas, retarget to the VRM, or produce model-authored choreography. It supplies real tracks we can use next for bounded amplitude selection, span preservation, transition planning and low-cost auditions. Pose interpolation and contact continuity between sampled frames, learned style, musical phrasing and subjective appeal remain open.

## Geometry repair superseding the first render

The v2 prototype had unintended changing ankle-foot and pelvis-attached segment lengths. Its arm/leg checks were too narrow. The investigation in `investigations/2026-10-19-dance-motion-rig-geometry.md` records the measurements. The repaired generator attaches feet to ankles, adds their bone links, translates hips/torso with pelvis and validates all19skeletal segment lengths. Seven focused tests pass.

Use `/Users/adom/Development/hermes-testing/runs/harness2-dance-motion-v3/comparison.mp4` and sibling tracks.json as the current prototype; `evidence/dance-motion-render-v3.json` records source/track/video hashes. All40frames decoded, four seconds at512x320, render pipeline1.88seconds. Parent inspected frames0,1,3. Earlier renders are preserved but superseded. Still no biomechanics, collision screening, continuous-contact proof between samples or human taste acceptance.

## Local-model-directed protected-span edit (2026-10-19)

`harness2/dance_edit.py` exposes one bounded operation: accent_arms with soft (0.20rad) or clear (0.45rad) strength. The host fixes the window to zero-based beats2–6 (seconds1–3). A sin² envelope rotates both elbows/wrists around their shoulder about world Y; this particular sign convention produces an inward/downward pulse. It does not generate new footwork or claim to improve taste.

`experiments/dance_model_edit_probe.py` asked local Gemma E2B for a pronounced accent while preserving footwork and approved opening/ending. It selected clear first try:104input/15output tokens,4.069seconds including3.484seconds model load. Native prompt evaluation was0.290seconds and output evaluation0.277seconds. Whole model/edit/render pipeline6.284seconds. No hosted calls.

The host changed only elbow/wrist positions at source frames21–59 of81. Allotherjoints, contact flags, timestamps, metadata and protected frames0–20/60–80 compare exactly equal. All19segment lengths still validate. The on-disk original hash remained unchanged. Output40frames/4seconds/512x320. Parent inspected decoded frames5,20,35: cyan original, orange edited; clearly visible central pulse, matching protected poses. This is sparse visual inspection, not a full-motion human taste audition or pixel-level preservation proof.

Media: `/Users/adom/Development/hermes-testing/runs/harness2-dance-model-edit-v1/comparison.mp4`. Evidence: `dance-model-edit-v1.json`; original and combined tracks in the media directory. The model chose a named operation and strength; trusted code authored the actual kinematic edit. No new Harness² refinement was performed in this trial.

Timing hardening: a deterministic review showed altered BPM could shift edits into protected frames even while the general geometry validator passed. The edit tool now rejects missing, boolean or nonmatching BPM/FPS/beat-count/duration metadata and computes bounds from authoritative timing constants. Thirteen edit/motion tests passed. Saved valid-input source/result hashes reproduce exactly after hardening; the render receipt retains the pre-hardening source file hash rather than being rewritten to imply a new render. Investigation: `2026-10-19-dance-edit-timing.md`.

The operations chat returned the MiniMax H3 setup locations. Parent independently inspected the saved node schemas and both API graphs; details and boundaries follow. No GPU work or H3 submission was performed.


## Portable reference bundle and animated scene (2026-10-19)

Sol added `harness2/motion_bundle.py`: copies immutable original/edited tracks and the comparison video into a fresh folder, records hashes, coordinates and timing, then independently verifies protected motion and decoded video metadata. Four focused bundle tests cover tampering, corrupted motion, wrong stream metadata and mismatched originals. The actual saved bundle passed its verifier: `/Users/adom/Development/hermes-testing/runs/harness2-motion-bundle-v1/manifest.json`; receipt `evidence/motion-bundle-v1.json`. This is a portable technical reference pack, not an H3-specific pack.

Parent exported the edited motion as animated GLB proxy meshes (18 joint markers and19bone cylinders). Initial v1 split the scene into37animations; the imported wrist remained static and positional checks failed by0.27069m. An explicit exporter flag now produces one scene animation. A fresh Blender import reproduced all81samples, with max joint error6.0064e-8m and bone endpoint error2.5278e-7m against original JSON precision. Export/import took1.49seconds. V3 is current; v1 and v2 receipts remain for diagnosis.

Artifact: `/Users/adom/Development/hermes-testing/runs/harness2-dance-gltf-v3/edited-motion.glb` (219020bytes,45animation channels). This proves sampled motion survives the format boundary. It is not an armature/skinned character, VRM, full interpolation check, or accepted H3 input. No model call or expensive render was needed this round.

## Actual H3 reference contract and next bridge

Here H3 is **MiniMax H3**, not Hunyuan. `evidence/h3-saved-input-contract-v1.json` preserves a filtered, hashed extract from `/Users/adom/ComfyUI-h3-setup/object_info.json`, `demo_api.json` and `clip2s_api.json`. These are saved contracts, not a live readiness check.

- ImageToVideo accepts optional first/last IMAGE frames. Width/height step32; its saved tooltip declares24fps and a17k+5 output-frame grid.
- ReferenceToVideo declares up to9reference images and3reference video frame batches. Video tooltip requires24fps and2–15seconds. Audio may accompany same-numbered clips. This is an IMAGE batch interface, not a GLB or joint-track importer.
- AddGuide declares image/clip anchoring with valid clip-length cropping, but is not wired in either saved API graph.
- Both saved workflows set USE R2V false, select ImageToVideo, and have neither first/last frames nor reference inputs wired. They therefore do not prove any conditioning handoff.

Next bounded test: create a single-actor RGB reference at24fps with explicit camera, coordinate and source-track manifest; preserve the unmodified tracks separately. Verify the intended reference checkpoint and a frame-loader-to-ReferenceToVideo connection before one short GPU generation. The present10fps side-by-side comparison is an audition aid, not this input. A successful load/submission must be followed by decoded generated output and a motion-fidelity comparison. No verified skeleton/pose-map/VRM/GLB ingestion path is established by these schemas.

Do not launch heavy Mac inference merely to test wiring. Preparing the RGB artifact and validating saved graph structure can stay local and cheap; actual model/checkpoint acceptance remains a separate bounded GPU experiment.


## Single-actor 24fps reference preparation (2026-10-19)

Sol added a render-only resampler that preserves the original source hash, records adjacent source indices/weights and retains exact values at16coincident samples. It produces96samples over4seconds (endpoint excluded, last time95/24s). Linear Cartesian interpolation causes up to1.1164mm segment-length deviation on this edited motion. These display samples deliberately have a separate schema and are not claimed to be contact-valid or rigid motion data. Eleven relevant resampler/motion tests passed.

A fixed-camera single-actor renderer checked projected geometry bounds over all96frames, with at least3% framing margin. The camera manifest and source mappings remain in `/Users/adom/Development/hermes-testing/runs/harness2-dance-reference-v2/`. Parent inspected decoded frame48; full-motion taste remains unevaluated.

Direct installed H3 source shows reference clips are truncated first by output frame count, then down to17k+5. An isolated execution of those actual statements (without importing/loading H3) returned96->90,107->107 with output limit124, and107->90 with limit90;4frames rejected. We therefore append11copies of the last rendered sample, yielding107frames at24fps (4.458333s). This preserves the96frame render stream and adds an explicit0.458333s final hold; it does not add new choreography or sample the original t=4endpoint.

The first master failed exact decoded-tail equality because default lossy H264 reconstruction varied across repeated frames. Raw-filter and lossless comparisons isolated encoding as the cause. Fresh v2 uses crf0 after YUV420 conversion: all107frames decode, and frames95..106 have identical decoded hashes. No claim of RGB-source pixel identity. Failed v1 and diagnostic remain. Whole v2 preparation2.83seconds; no model inference.

Video: `/Users/adom/Development/hermes-testing/runs/harness2-dance-reference-v2/reference.mp4`. Evidence: `dance-reference-v1.json`, `dance-reference-v2.json`, `dance-reference-review-v2.json`. Installed source and saved schemas support LoadVideo -> GetVideoComponents output0 (IMAGE) -> ReferenceToVideo dynamic input `ref_videos.ref_video_0`. A sibling staged node patch declares the upload filename and routing; it has NOT been uploaded, validated against a live server, or submitted. The operations chat received the artifact and exact limits with no ACK requested. A matching model architecture or saved workflow still does not prove successful reference-conditioned inference.


## Local visual critique pilot and failure (2026-10-19)

Sol prepared a bounded native Ollama image runner; parent inspected and froze six images from the existing comparison: two protected-pose frames and one clear arm-accent frame, each normal/flipped. Ground truth comes from exact protected joint equality and arm positions (sum of wrist lateral offsets1.08m original versus0.59818m edited), with visual checks. Source image hashes, model digests, full prompts, raw replies and timing are retained in `evidence/dance-vision-v1.json`.

| Model | Correct /6 | Edited frame /2 | Unchanged controls /4 | Behavior |
|---|---:|---:|---:|---|
| Gemma E2B local |4|0|4|Answered same every time|
| Gemma E4B local |1|1|0|Answered left every time|

All12responses were strict schema-valid JSON. Neither beats the corresponding constant-answer baseline; do not interpret E2B4/6 as useful motion recognition. Native prompt counts188 each include the endpoint's reporting convention; separate vision-encoder cost is unavailable. E2B first response3.843s, subsequent0.778–0.811s;E4B first5.465s, subsequent1.003–1.013s. These tiny cached/warm samples are not service percentiles or5090 estimates.

Eight diagnostic calls followed with raw receipts kept separately: both models named red/blue color cards correctly, demonstrating image dependence for simple inputs. Both gave a directionally correct width description of the normal accent in free text, but both failed the flipped version. Removing constrained JSON is not a sufficient repair. See `dance-vision-diagnostic-v1.json` and explicit parent interpretation in `dance-vision-diagnostic-review-v1.json`. No fine-tuning, Harness² adaptation, or human taste judgment occurred. All20calls local; hardware/energy cost unmeasured.

Implication: keep kinematic invariants and host verification authoritative. A local visual assistant can propose descriptions/questions, but cannot currently approve even these simple motion edits unaided. Next useful comparison would separate each actor into matched crops, use semantic feature outputs before a host comparison, and evaluate on fresh poses/orientations; also compare a stronger vision model under the same images before scaling spend. Do not train on these model judgments as truth.


## Stronger vision baseline and crop treatment (2026-10-19)

Twelve OpenRouter calls repeated the exact six-image comparison with hosted Gemma4 26B-A4B and31B, using the same text and schema. Current model metadata advertised image input; prices and supported parameters were captured before execution. Per-request price filters,96output-token cap,45second hard deadline,12call cap and0.10USD reported-cost stop bounded the run. Actual combined reported cost was **$0.0004018675**. These are hosted-model observations, not expected local quantized performance. Provider routing differed:26B usedDarkbloom/NextBit;31B usedNovita. [26B model listing](https://openrouter.ai/google/gemma-4-26b-a4b-it), [31B model listing](https://openrouter.ai/google/gemma-4-31b-it).

Both models identified the clear edited actor correctly in both orientations (2/2), but falsely chose right in allfour unchanged controls (0/4). Thus both2/6overall, and neither qualifies as an acceptance verifier. Reported input counts varied by route:26B389or495,31B242or389; alloutputs10tokens. Wall times:26B0.830–1.568s and31B1.195–2.209s. No latency percentile or causal model-size comparison is implied. Raw provider usage/costs remain in `dance-hosted-vision-v1.json`.

Sol implemented a different interface: split each existing image into two256x320crops, classify each as narrow/wide/unclear, and let trusted code compare the two classes. Parent inspected complete figures in the crops before24local calls. Both E2B andE4B returned narrow for all12crops each. Each therefore produced same for all6derived comparisons, scoring4/6on controls but0/2on edited examples. Absolute narrow/wide wording may introduce threshold ambiguity;2/12per-crop agreement with our labels is not a general visual-capability score. Pair inference now costs two calls, so correctness must improve to justify the latency. Initial token and wall-time measurements are in `dance-crop-vision-v1.json` and the comparison summary.

An additional8local calls changed only enum order from narrow/wide/unclear to wide/narrow/unclear on fourmatched crops permodel. Allanswers remained narrow. This does not support an enum-order explanation. Evidence: `dance-enum-order-v1.json`; retained investigation includes hypotheses and unchanged baseline.

Decision: stop retries on these sameimages. None of these vision paths is an authoritative motion-quality checker. Keep exact geometry/preservation checks; visual models may draft descriptions or candidate questions. This round used32local calls and12hosted calls; local energy/hardware cost unmeasured. No Harness² adaptation or fine-tuning was performed.

Luna independently proposed6future geometric cases from source only: identical restrained/broad controls, edited actor on either side, soft-versus-clear, and a footwork-only change. Some proposed time2.0s/clear configurations overlap existing development exactly, so they are NOT untouched holdouts merely because an independent author proposed them. Use them as regression/control ideas; freeze genuinely new times, views and appearances before the next evaluation. Publish a clear task criterion to the model (that is not label leakage), but keep per-case answers and evaluator code outside editable harness prompts. Validate projected evidence where the task is image-based; a world-coordinate metric need not be visually identifiable from every camera.

Next broader development should prioritize multi-step actor staging and reusable gesture/motion vocabulary. If returning to visual acceptance, test fresh poses with a clearer geometric criterion and explicit abstention/calibration; do not simply optimize scores on this six-image set.


## Model-directed two-actor staging (2026-10-19)

Expanded from one isolated motion edit to a six-second scene with two actors, fixed relative placement and three ordered two-second cues. Sol implemented `actor_staging.compile_staging`: models choose symbolic identities, anchor sides, gesture and soft/clear variation; host code resolves coordinates at anchor±0.85m and owns timing. Strict validation rejects stale revision, duplicate/missing slots, unknown identities, extra fields and invalid geometry. Eleven staging/actor-intent tests passed. No walking/path-planning claim: actors stay planted throughout.

Luna authored four task fixtures independently: a greeting, mirrored roles with offset anchor, nod-before-wave, and a quiet sequence. Parent verified expected plans compile before model calls. Last two were kept out of future editor inputs, but allfour are now observed baseline cases, not untouched evaluation. No editor or Harness² refinement ran in this round.

Both local Gemma E2B and older Qwen3 8B passed3/4first attempts and4/4after at most one correction. Both initially used duplicate/one-based slot values on the task phrased first/second/third. The host's structural error named required slots0/1/2; both corrected them without being supplied the desired plan. Each model then repaired a deliberately injected missing_actor cue while preserving every other JSON value and array order. The injected failures are separately labeled and do not inflate natural-repair success. Twelve local calls total; no hosted fees.

| Model | Initial prompt tokens | Initial output tokens | First-attempt wall time | Observed decode tokens/s, all6calls |
|---|---:|---:|---:|---:|
| Gemma E2B |254–265|256–261|5.05–7.62s|53.24–59.56|
| Older Qwen3 8B |250–262|208–213|9.76–12.36s|15.78–25.75|

Exact initial character lengths, load/prefill/decode counts, raw replies and model digests remain in `actor-staging-v1.json` and `actor-staging-summary-v1.json`. These are one small Mac run, not sustained rates or5090forecasts. Qwen decode varied materially across calls; no cause established. No Blender render ran concurrently with inference.

Parent rendered two accepted Gemma plans, including reversed actor order and offset anchor. Renderer preflight found and repaired an implementation mismatch: it previously assumed fixed left-to-right list order/origin; camera orientation also needed to match world+x=screen-right. The investigation preserves isolated validation evidence (1/4before,4/4after) and actual projection checks after repair.

Eachvideo48frames/8fps/6seconds/512x320. Independently checked actual Blender world-joint readback acrossallframes: protected joints and nonacting actors unchanged within1.15e-7m, segment lengths within1.16e-7m, neutral restored atframes0/15/16/31/32/47. Gesture slots changed only their permitted arm/head joints. First and mirrored scenes rendered/encoded/verified in a few seconds each. Parent inspected decoded frames8/24/47: wave, correct actor sides and neutral return are clear; nod is subtle at this size. No claim of realistic acting, continuous collision-free motion or human taste acceptance.

Media: `/Users/adom/Development/hermes-testing/runs/harness2-actor-scene-v1-plinth_pair_intro/scene.mp4` and `harness2-actor-scene-v1-gallery_roles_reversed/scene.mp4` under the same runs root. Evidence: `actor-staging-render-v1.json` and `actor-staging-review-v1.json`. This is an offline technical staging preview, not a persistent viewer, interruption integration, skinned production character or H3-generated scene.

Next useful efficiency experiment: a compact but equally expressive intent representation that lets the host bind revision and infer the opposite-side actor and cue slots from ordered array position. That could eliminate repeated IDs/timing fields and this ordinal-index failure. Preserve allplacement/gesture/variation choices; test canonical-plan equivalence and stale-request rejection before comparing latency. Separately, the actual Harness² improver can test learned instruction changes against fixed guidance and bounded repair on freshly frozen ordinal briefs. Do not call a manually shortened protocol an adaptation gain.

Latency planning: a260token plan alone needs about43.3decode tokens/s to finish within6seconds, before prefill, loading, validation or rendering. A100token equivalent would need16.7tokens/s for that same decode-only budget. These are arithmetic requirements, not model/hardware forecasts; batching and prestaging allow the language model to work ahead while deterministic animation runs at its own frame rate.

## Compact staging comparison (2026-10-19)

Sol added an equivalent shorter protocol: `left` selects one actor, the other actor is inferred, and three ordered `[actor, gesture, variation]` arrays supply the cues. The host binds a frozen scene snapshot and rejects changed current facts, even anchor-coordinate changes with unchanged revision. Ten compiler tests pass. Exhaustive enumeration of both side assignments and every three-cue actor/gesture/variation combination across the four existing scene fixtures produced **13,824 exactly equal canonical plans**. No gesture or variation was removed to improve speed.

Twenty local calls compared full and compact formats on the same four previously observed cases. Protocol order alternated within each model and reversed between models; at most one immediate correction was allowed. Prompts, schemas, model digests, native timing and all failed replies are in `actor-staging-compact-v1.json`; derived metrics and fresh-fixture freeze are in `actor-staging-compact-summary-v1.json`.

| Local model / format | First correct | After at most one correction | Initial output tokens | Median first response |
|---|---:|---:|---:|---:|
| Gemma E2B full | 3/4 | 4/4 | 256–261 | 4.94 s |
| Gemma E2B compact | 2/4 | 3/4 | 51–54 | 1.37 s |
| Older Qwen3 8B full | 3/4 | 4/4 | 208–213 | 9.37 s |
| Older Qwen3 8B compact | 4/4 | 4/4 | 66–70 | 3.56 s |

The compact initial prompt is slightly LONGER: 933–992 characters and 271–283 native tokens, versus full 907–966 characters and 250–265 tokens. Savings are in generated output, not initial transcript length. Median output reduction is about 80% for E2B and 68% for Qwen. Native median decode time falls from 4.42 to 0.87 s for E2B and 8.52 to 2.62 s for Qwen. These are tiny reused-case measurements with cold-load/cache/time effects, not sustained service benchmarks or 5090 projections. At 70 output tokens, the decode-only requirement for a six-second planning horizon is about 11.7 tokens/s; input processing and other work still consume time.

The compact E2B failures are valid but semantically wrong plans: the first two requested cues are swapped, putting the left actor first. One generic correction recovers the quiet case; the gallery case remains wrong. Independent expansion through the old compiler agrees with the compact result, ruling out a compact-only compiler error. All Qwen compact cases pass. The investigation retains the hypotheses and primary evidence. A concise interface is therefore a useful Qwen candidate, but cannot yet replace the full E2B interface on reliability grounds.

Crucial boundary: the expected fixture plan detects those semantic mistakes in this experiment. Production structural validation alone would accept them. Do not claim the host can automatically detect arbitrary natural-language misunderstanding without an independent semantic check, constrained task authoring or review. No new rendering was required: accepted plans are exactly equal to canonical fixture plans. No model learning, Harness² adaptation, GPU rental or paid provider calls occurred in this comparison.

Luna separately authored four new development and four evaluation cases covering ordinal language, audience-relative sides, later amendments and repeated actor cues. Their expected plans compile, and their source hash is frozen in the summary before model use. Evaluation cases remain unseen by solvers/editors; this is a within-family split, not new-family generalization. Next actual Harness² experiment should learn guidance with development-only failures, compare fixed/repair/adapted conditions, and retain the compact/full choice as a separate experimental factor. The new development cases and the observed gallery ordering error provide useful material for that bounded round.
