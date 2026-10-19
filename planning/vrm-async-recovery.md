# External interruption and stale-result rejection in a real VRM render

Completed2026-10-19 without model inference. A Python process starts the actual Deno/WebGPU renderer; when the renderer signals frame8 readiness, Python atomically publishes an interrupt message with revision2. After its acknowledgement appears, Python publishes a simulated late gesture response from revision1. This is real cross-process filesystem delivery while rendering, not just a preloaded event array.

Observed: interrupt applied at frame9; stale gesture rejected at frame12. All39frames from9through47 retain the saved idle normalized pose, no registered mixer and root[0.35,0,0]. This asset has22mapped bones; maximumDifference is taken across all22 normalized transforms. Visual inspection of decoded frames8/47 shows a raised arm then lowered arms. Output:48frames,640x360,3.2seconds. Host pipeline elapsed1.49seconds, including renderer startup/encoding: it runs faster than playback here, so do not interpret frame index as wall-clock response latency.

Source: experiments/vrm_async_scene.js; runner: experiments/vrm_async_probe.py; evidence: evidence/vrm-async-live.json. Verification requires every frame0–47, both event outcomes, preserved post-stop pose/root and absent mixer. Negative receipt tests prove status labels alone cannot hide resumed motion or missing frames. Shared GPU lock,90second outer deadline and process-group termination bound failure behavior.

Video: `/Users/adom/Development/hermes-testing/runs/round6/eidoverse-video/work/eidoverse-harness2-async-v1/avatar_probe.mp4`.

Boundaries: finite offline film, fixed trusted event schema, single writer, two events. The delayed response is synthetic, not a delayed API request. This does not establish long-lived live display, network delivery, speech interruption, heartbeat/lease expiry or concurrent writers. It applies the same revision/neutralization principles as the Python EventRuntime simulator but is not yet a shared production runtime. Immediate neutral restoration is a deliberate snap; a blended recovery needs its own tests.
