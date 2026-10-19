# Executable phrase library pilot — 2026-10-19

The local model can now choose a four-move score that becomes real, verified procedural joint motion. This is a useful actor-control building block; the current motion is a planted technical proxy, not compelling choreography, a skinned character, an H3 output, or a human-approved dance.

## What exists

Sol built five two-beat phrases at120BPM: rise(rest→open), sway(open→open), pulse(open→open), settle(open→rest), hold(rest→rest), each soft/clear. The model chooses four `[move, variation]` pairs. Host code owns geometry, timing, transitions and the frozen library. It compiles81samples at20fps over4seconds and retains source clips and hashes. Checks cover exact endpoint poses, all19skeletal segments, planted ankles/foot markers, finite bounded joints, real clip joins, and neighboring phrase preservation when variation changes. Fourteen phrase/motion/readback tests pass. Sampled displacement checks do not prove physical balance, collision freedom or smooth continuous velocity.

Luna independently authored8executable briefs and2infeasible diagnostics before inference. The oracle allows multiple plans where prose allows choice. Enumeration found1–32accepted plans per executable brief and zero for the two impossible transition requests. These latter cases were offline-only: the moves-only model protocol cannot express an explicit refusal. One amendment sentence was clarified before inference to match its intended unchanged constraints; exact final source hashes are recorded.

## Model results

All models saw the same public catalog and prose, never the acceptance constraints. At most one correction: structural errors would be returned; valid-but-wrong plans receive only a generic reread request. The experimental oracle triggers that retry, so this does not establish automatic production detection of arbitrary prose misunderstandings. These are fresh within-catalog first tests, now observed; no Harness² learning or fine-tuning occurred this round.

| Model / runtime | First correct | After one correction | Median first wall | Initial input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|
| Gemma4 E2B / Mac |5/8|5/8|1.00s|184–204|26–28|
| Older Qwen3 8B / Mac |7/8|7/8|0.88s|191–209|23–27|
| Qwen3.6 35B-A3B / OpenRouter |8/8|8/8|1.00s|187–205|23–80|
| Qwen3.6 27B / OpenRouter |8/8|8/8|0.90s|187–205|23–41|
| Gemma4 26B-A4B / OpenRouter |8/8|8/8|0.98s|196–333|26–32|
| Gemma4 31B / OpenRouter |8/8|8/8|1.06s|189–208|26–32|

Initial message text is778–879characters. Native local decode medians are0.446s(E2B) and0.512s(Qwen8), approximately60.6 and46.9decode tokens/s in this run. These are tiny warm/cold/cache-sensitive samples, not sustained rates. Hosted counts include provider-specific accounting and formatting; provider/hardware/quantization differ. None of these timings forecasts a5090 deployment. A28-token score requires7decode tokens/s for a4-second lookahead, before input processing/loading/validation; this is arithmetic, not an observed requirement guarantee.

All52proposals compiled, including semantically wrong ones. E2B missed requested variation, preserved-final variation after amendment, or held intro. Qwen8 replaced a repeated sway with pulse. Raw choices equal compiled/saved choices, and generic retries repeat those errors. Preserve format validity separately from brief adherence. Hosted8/8 on this small easy catalog does not distinguish the four larger candidates or prove broad reliability.

32hosted calls reported a total **$0.002572911**;20local calls incurred no provider charges, with local hardware/energy cost unmeasured. The hosted runner checked live model metadata and price ceilings, limited context/output/calls, and would stop on missing cost reporting or$0.25reported spend. No RunPod rental, model download or H3 submission occurred.

## Rendered evidence and next work

The first brief's accepted local E2B and Qwen8 plans were rendered side by side: cyan/A on the left and orange/B on the right. Both choose rise, sway, pulse, settle; their pulse/settle variations differ.40encoded frames at10fps,512×320,4seconds. Actual Blender world-joint readback agrees with source tracks within1.08e-7m; segment error is below1.35e-7m. Render/encode/check took1.67seconds. Parent inspected decoded frames0/10/15/22/28/39: rise and return are clear, lateral/pulse differences subtle. Readback checks scene joint-object transforms and joint-derived segment lengths, not cylinder-mesh endpoints or all encoded pixels. Sparse frame inspection is not a full-motion taste assessment. No human preference or blind audition has been collected.

Video: `/Users/adom/Development/hermes-testing/runs/harness2-dance-phrases-v1/comparison.mp4`. Receipts: `dance-phrase-model-v1.json`, `dance-phrase-hosted-v1.json`, `dance-phrase-summary-v1.json`, `dance-phrase-preview-v1.json`; raw motion/readback files remain beside the video. Source clip generation is procedural, with no downloaded motion assets.

Next priorities: (1) broaden authored motion beyond planted arms, with changing support feet, durations, headings and stronger musical accents; (2) keep approved spans fixed while comparing two contextual variations; (3) freeze genuinely new briefs before an actual H2 refinement experiment on the local failures; (4) collect human keep/change/neither judgments with music and timestamped reasons. Separate brief compliance, mechanical validity and taste. The four hosted candidates are all viable for the next harder test; this pilot offers no quality-based reason to rent a GPU yet. Future local Q4 trials must repeat these checks on their actual weights/runtime.
