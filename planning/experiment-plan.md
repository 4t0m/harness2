# Experiment plan

## Compare one change at a time

Use the same frozen fixtures, tool schemas and independent oracle across:

1. Fixed minimal harness + base small model.
2. The same model + bounded structured repair feedback.
3. The same model + Harness² adaptation, initially k=1 sequential.
4. A fine-tuned model + the unchanged fixed harness.
5. Fine-tuned model + the best independently validated harness.

Luna is a practical reference executor; Sol can help design candidate instructions or tools. Judge programmatically where possible, rather than asking the same model whether it succeeded. Track model and harness changes separately. First qualify a compatible provider route: the existing Hermes ChatGPT sign-in does not automatically authenticate this repository.

## Harness resilience

Keep task facts host-owned. Use ID references and versioned snapshots, strict JSON, finite numeric bounds, exact allowed fields, and small error codes with field paths. Bound attempts and wall time; stop semantic repeats and preserve every failed attempt. Never silently shrink clearance, change a target or drop a requested action to accept a proposal.

Make completion a host check. Record first-pass success, recovered success, rejection, unsupported, timeout, false completion and escalation independently. Prompt text, proposed tool calls and external content cannot redefine the oracle. Harness² may edit the allowed instruction/tool-guidance surfaces; acceptance data remains outside those surfaces.

The upstream Codex benchmark executor disables its sandbox and allows broad network access. That is unsuitable as the default for our narrow actor tests. Implement a constrained executor before exposing personal workspaces or external controls; the deterministic bootstrap demo does not invoke that executor.

## Future dual-5090 deployment

Verify model, quantization, served context, structured-output behavior and endpoint compatibility on the actual machine. Measure cold load, prefill, decode and end-to-end completion independently. Compare one worker, two independent workers and multi-GPU execution only when supported; two GPUs do not imply twice the speed. Begin with small offline tasks before giving the agent a live avatar.

Upstream OpenCode uses provider/model routing; its Codex path expects a Responses API endpoint. Ollama or another local server needs a verified compatible route or adapter. No local API behavior is assumed from a generic OpenAI-compatible label. Keep endpoint secrets outside Git.

## Fine-tuning and evidence

Keep initial failures, explicit corrections, final proposals and independently checked outcomes. Label scripted fault injection distinctly from model failures. Split train/dev/test by whole task families, identities and fixture variants before any QLoRA work; near-duplicate scenes are not independent held-out tests. Exclude credentials, private conversations and personal assets. Respect model and data licenses when selecting the eventual training stack.

Select training traces only after validation. Do not train the model to echo success receipts without producing a correct artifact. Test whether fine-tuning reduces corrections, context and latency while preserving abstention on unsupported actions.

## Next concrete milestones

- A custom synthetic actor adapter runs deterministic fixtures through Harness²'s actual loop.
- A bounded model executor passes the same fixtures with Luna or a verified compatible local endpoint.
- Compare fixed/repair/adapted harnesses on untouched held-out cases with original failures retained.
- Then connect one flat-avatar adapter and author a few meaningful move variants.

Current state (2026-10-19): actual model-backed solver and guidance editor have run through Harness², but no general adaptation gain is established. Flat command/readback and model-selected procedural Blender previews have executed; protected-span motion variation is verified on one rig. Local serving, training, richer avatar motion and human taste evaluation remain unfinished. See capability-status.md for current evidence and local-model-experiment-atlas.md for the expanded map.
