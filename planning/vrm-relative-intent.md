# Humanoid VRM relative-intent bridge

Completed2026-10-19. This reuses the earlier Hermes round6 VRM renderer; it is a new Harness²-side model-intent integration, not discovery of a new render engine. A read-only Sol audit initially missed isolated Deno outside PATH; parent located the runtime and prior successful receipts under runs/round6/eidoverse-deno and experiments/round6/eidoverse-salute. Verified live use supersedes the initial runtime uncertainty.

The bundled claude.vrm is a technical rig asset, not the intended custom character design. Audit found22humanoid bone mappings and18expression presets; checked-in clips include idle, salute and wave_goodbye. The documented dance clip is absent. Do not claim dance support.

One Gemma26 request chose `{gesture:wave_goodbye,side:right}` for a farewell to the right of an anchor. Host compiler uses anchor x=0.1 and center offset0.25 to derive x=0.35, within the renderer's±0.6 bound. This is point-relative root placement, not edge clearance, path planning or collision avoidance. The model cannot override coordinates. Unknown intent, extra fields, nonfinite/invalid host geometry and unreachable positions reject.

The pinned trusted `tools/eidoverse_mcp.py` rendered12frames at640x360/15fps on Apple M2 Max WebGPU with its existing lock and90second limit. Parent independently recomputed receipt hashes. Final rootPosition=[0.35,0,0] and animated right-arm quaternion differ from load pose. Final still inspected: rig visible, arm raised, body to screen-right. The anchor is conceptual and not drawn; placement assertion rests on state readback. No persistent avatar session, interruption, voice or smoothness claim.

Model input59tokens/output28,1.34s hosted response, reported$0.00001887. Output needed exact-fence repair. Output directory: `/Users/adom/Development/hermes-testing/runs/round6/eidoverse-harness2-relative-v1/`; video `avatar_probe.mp4`, three PNGs and state/hash receipt. Evidence: evidence/vrm-intent-live.json. Reproducible entry: experiments/vrm_intent_probe.py; it refuses existing outputs.

Next material extension: qualify more animation clips or bounded normalized-bone controls with interruption/neutral recovery, or retarget to a chosen character. Do not infer model license, asset design approval, or a reusable dance corpus from this technical rig test.
