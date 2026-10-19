# Model-controlled, protected-span gesture variation

Completed2026-10-19. Gemma26 selected `restrained` from a two-option motion catalog for a brief asking for the most restrained available middle gesture. Host compiler maps only the variation enum to one fixed joint/axis/keyframe and protects frames1–12/36–48. It pins the source Blender asset by SHA-256 and rejects extra fields, unknown variants, duplicate keys and stale source identity. The model cannot supply code, paths, arbitrary joints or timing.

A fresh Blender process applied the edit and saved a new scene. Another process loaded original/revised scenes and compared all object transforms for48frames, then rendered12samples. Opening/ending transforms and all non-arm object transforms remained equal (rounded7decimals). All changed frames were13–35. Independently decoded RGB comparison against the isolated original found identical pixels at1/5/9/37/41/45 and differences at13/17/21/25/29/33. Source asset hash unchanged. Visual inspection of frame25 confirms lower arm angle. Video decodes as12frames,320x320,2seconds.

Model call:102input/18output tokens,0.65s hosted response,$0.00001476 reported. Raw JSON was fenced and accepted only after exact-fence normalization. No extra inference for correction. Two contract tests passed; actual Blender and pixel receipts provide runtime evidence beyond unit tests.

Artifacts: `/Users/adom/Development/hermes-testing/runs/harness2-model-variation-v1/preview.mp4`, `revised.blend`, `plan.json`, stage logs and receipt. Repository evidence: evidence/gesture-variation-live.json. Entry point: experiments/gesture_variation_probe.py. Never rerun into existing output.

This demonstrates natural-language brief -> finite variation selection -> trusted motion edit -> isolated verification/render. The descriptions supplied the intended meaning of the variants; the model did not infer attractiveness from video. It is not a learned choreography generator or taste judgment. The preview is sparse6fps with noisy1-sample lighting. Next generalization requires multiple gestures/rigs and richer phrasing, plus human audition rather than accumulating near-identical arm edits.
