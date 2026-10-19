# Dance edit timing metadata check (2026-10-19)

Expected: `edit_arms` changes only the fixed prototype's beats 2–6 (times 1.0–3.0 s at 120 BPM) and rejects altered timing metadata. Reported concern: `dance_motion.validate` may accept edited metadata while `edit_arms` uses `sequence['bpm']` to decide the span. That could let a valid-looking source move the edit to protected frames. This matters because the host must own the edit window.

Context: `dance_edit.py` is an uncommitted new file; recent committed motion changes are `8fe4514` and `16b0353`. No prior timing-metadata fix has been attempted. Repository `AGENTS.md` requires authoritative acceptance checks outside editable surfaces.

## Diagnostic plan

1. **Validator already rejects altered timing.** Copy a generated sequence and set `bpm=240`; call `dance_motion.validate`. Rejection confirms this; acceptance rules it out.
2. **Validator accepts metadata, but editor uses fixed prototype timing.** On the modified sequence, call `edit_arms` and inspect changed frame indices. Changes only within indices 21–59 would confirm fixed timing; changes near indices 11–29 rule it out.
3. **Validator accepts metadata and editor trusts altered BPM.** For the same modified sequence, look for changed frames before index 20 and a passing final validation. Both observations confirm a scope bypass; rejection or no early changes rules it out.
4. **Other timing fields create an independent mismatch.** Change each of `fps`, `beats`, and `duration_seconds` alone and try validation/editing; acceptance would show that exact metadata checks are needed beyond BPM.

Use `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python` with an inline deterministic snippet. No model, renderer, or network call.

## Findings

The deterministic probe found:

- `bpm=240`: `dance_motion.validate` accepted; `edit_arms` accepted and changed frames 11–29. This confirms hypothesis 3 and rules out hypotheses 1 and 2. The edited result also passed the full motion validator.
- `fps=40`, `beats=16`, and `duration_seconds=8.0`: each was accepted by both validator and editor. These fields did not change the current edit indices, but their metadata was inconsistent with the prototype. This confirms hypothesis 4's independent metadata gap.

Conclusion: high confidence in a local scope bypass caused by trusting mutable timing metadata. The fix is an exact, type-sensitive entry check against `dance_motion.BPM/FPS/BEATS/DURATION`, followed by beat calculations from the authoritative BPM. Retain full motion validation and independent protected-frame checks. The existing valid prototype should produce identical edited hashes.
