# Event runtime experiment

CPU-only reference behavior for an eventual Hermes or dedicated interactive runtime. No model, microphone, speech, renderer or provider was used. Reproduce with `.venv/bin/python -m harness2.event_runtime`; evidence is evidence/event-runtime-replay.json.

Host owns request ID, scene/event revision, decision deadline, hold duration and action vocabulary. Model response contains only an action. New requests supersede earlier pending decisions; an interruption clears pending requests and cancels active action. Duplicate, invalid and expired responses cannot acquire a lease. The latest active gesture may continue until a replacement decision, explicit interruption or lease expiry. The model cannot extend its own deadline or duration.

Seven tests cover interruption before/after response, deadline equality, out-of-order responses, duplicate calls, invalid or authority-expanding outputs, lease expiry, detached snapshots and the combined replay. No retries or formatting repair are built into this critical path yet: a fresh request would be required, with a new host budget.

This is a logical-clock simulator, not a real-time scheduler. Expiration occurs when advance is called; it does not run a background clock. A live integration must schedule deadlines independently of model completion and verify actual neutral/mute/cancel behavior. Its command receipts are simulated desired actions, not confirmation of browser or audio output. In particular, listen/nod are abstract actions and do not imply the current flat avatar adapter implements them.

Next controlled comparison: generate held-out event episodes with delayed response delivery, interruption and scene changes. Compare naive apply-every-response, this host-gated runtime, and model policy variants without weakening host checks. Score useful timely actions as well as stale-action rejection so doing nothing cannot win. Harness² adaptation can change compact decision guidance between episodes, not host clocks, accepted actions or oracle.
