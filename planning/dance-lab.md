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
