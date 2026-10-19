# Local Mac inference and avatar execution — 2026-10-19

Ollama0.30.10 was reachable at127.0.0.1:11434 outside the tool sandbox. Initial sandbox probes returned Operation not permitted, which was not evidence that the service was down. Ports8080/1234 refused connections in the authorized external probe. Exact installed model identities/digests are saved in evidence/local-menu-model-metadata.json.

Four creative-menu cases, rotation0, native /api/chat, think=false, temperature0, num_ctx2048, num_predict96, keep_alive2m,60second hard call deadline. These are the same explicit-constraint cases used for hosted menu trials, but generation settings/model/tokenizers differ; this is not a controlled ranking of all models.

| Installed model | Strict correct | First request / load | Later request wall time | Reported decode rate |
|---|---:|---:|---:|---:|
| hermes-lab-qwen3-8b (Qwen3 8B Q4_K_M) |3/4|4.18s /3.48s|0.70–1.26s|30.8–52.2tok/s|
| hermes-lab-qwen30 (Qwen3 30B-A3B Instruct2507 Q4_K_M) |4/4|11.99s /11.39s|0.56–0.72s|59.9–71.2tok/s|

All responses were valid JSON with no thinking content or format repair. 8B chose the30GPU-second final render despite a12GPU-second limit; semantic failure preserved. Each output was only9tokens: these are short-call reported rates, not sustained-generation benchmarks. Native prompt evaluation counts/durations are stored per call; caching and server accounting may affect them. Context capability metadata from model tags is not the2048trial setting.

The installed30B model is older Qwen3, not the recent Qwen3.6MoE exploration target. Do not rename it or extrapolate speed to a dual5090 rig. No paid provider request, model download or fine-tune was needed. Electricity/total local cost was not measured.

## Actual local-model avatar bridge

experiments/vrm_intent_probe.py --local-qwen30 uses Ollama's OpenAI-compatible chat route with the existing transport. Returned strict `{gesture:wave_goodbye,side:right}`. Host compiled anchor0.1 plus offset0.25 to x0.35, rendered the existing VRM clip and independently rehashed artifacts. State/readback and final still confirmed a raised-arm gesture at the requested root position. This single call used52input/15output tokens and4.73s end-to-end; the compatibility route does not expose native load/prefill/decode breakdown, so do not compare that time directly to warm native9token calls.

Evidence: local-menu-qwen8-v1.json, local-menu-qwen30-v1.json, local-menu-model-metadata.json and vrm-intent-local-qwen30.json. Video: `/Users/adom/Development/hermes-testing/runs/round6/eidoverse-harness2-local-qwen30-v1/avatar_probe.mp4`. Local output cost field is null (no provider billing metric), not a measured zero total cost. This remains offline avatar rendering, not persistent conversation/voice.

## Compute coordination

The authorized operations chat replied that it has no currently verified LLM endpoint, current RunPod quote/cap or qualified Qwen/Gemma serving recipe. Historical Comfy worker evidence does not establish those. No pod created. No credentials copied. Current local serving is enough to continue contract/recovery trials; rent only for a defined speed/size comparison with a current inclusive cap, deadline and cleanup owner.
