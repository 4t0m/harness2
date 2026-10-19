# Creative retry probe: Markdown-fenced JSON rejection

## Frame

Expected behavior: a valid intent selecting the sole failed `slot_2`, with a new retry ID,
should be applicable after strict validation. Actual behavior: the saved live receipt has
`finish_reason=stop` and the correct three intent fields, but the response is wrapped in one
` ```json ` / ` ``` ` block and strict `json.loads` rejects it as “response must be one strict
JSON object.” This matters because the model selected the expected failed item, while the
host rejected only the presentation envelope; retaining a strict intent validator keeps the
production state machine authoritative.

## Context reviewed

- The original live receipt is `evidence/creative-retry-live.json`; it records the raw fenced
  content and rejection. Preserve it unchanged as the model-call record.
- `experiments/creative_retry_probe.py` currently passes the full completion directly to a
  strict JSON parser. The host then checks exact fields, expected failed target and fresh ID.
- `AGENTS.md` requires preserving failures and separating model claims from verified output.
- `git log` had no history entries for these probe files because the current files/evidence
  are untracked. There has been one model call and no formatting repair attempt.

## Competing hypotheses

1. **A single Markdown fence is the only blocker.** The response body is valid JSON once one
   full-response `json` fence is removed. Confirm if exact fence normalization yields the
   same intent and the original strict validator accepts it. Rule out if parsing or field
   validation still fails.
2. **The fenced body has an independent schema/JSON defect.** After removing only an exact
   fence, strict decoding or exact-field validation still rejects it. Confirm with that
   normalized body; rule out if it parses and validates unchanged.
3. **The model response uses broader wrapping (multiple blocks, prose, malformed fences).**
   A normalization that scans/extracts JSON could accept content the contract should reject.
   Test multiple fences, unmatched fences, and leading/trailing prose; all must remain
   rejected in repair mode. If the saved response is precisely one whole-response fence,
   this does not explain this receipt but remains a critical repair-boundary alternative.
4. **The selected target is wrong despite valid formatting.** After exact normalization,
   host validation may still reject because the intent does not select the unique failed job.
   Confirm with a fenced wrong-target intent; rule out for the saved receipt if `slot_2`
   validates and the trusted retry preserves all unrelated state.

## Diagnostic plan (written before tests)

1. Read the preserved receipt and capture its raw string exactly. Confirm it contains one
   opening fence, one closing fence, no outer prose, and the JSON object has exactly the
   required keys. This distinguishes the observed formatting from malformed/trailing text.
2. Add a disabled-by-default exact-single-fence normalizer. In repair mode only, accept
   either unfenced strict JSON or a full-response ` ```json` fence with a single JSON object
   and no surrounding prose. Do not search for or extract arbitrary braces or code blocks.
3. Unit-test: saved response accepted only with repair mode; malformed JSON rejected;
   multiple/unmatched fences and trailing/leading prose rejected; wrong failed target still
   rejected after normalization; a valid fenced target applies through trusted retry and
   preserves completed receipt plus unaffected jobs.
4. Run ` .venv/bin/python -m unittest tests.test_creative_retry_probe -v ` and
   `git diff --check`. No provider/API call is part of these diagnostics.
5. Build a separate offline replay evidence record from the preserved receipt and current
   deterministic code. Label it `deterministic_repair_replay`, retain the original live
   content and rejection, and explicitly state no model retry or paid call occurred.

## Findings

- The preserved raw response is one whole-response `json` fence around a valid three-field
  object: `operation=retry_failed`, `job_id=slot_2`, `new_job_id=slot_2_retry_1`. The recorded
  live state independently shows `slot_2` as the sole failed job. No prose or extra field is
  present. This supports hypothesis 1 and does not support hypothesis 3 for this receipt.
- With repair disabled, the same response remains rejected; with the optional exact-fence
  normalizer, the embedded JSON passes the unchanged exact-field, expected-target, and
  fresh-ID checks. This supports the syntax-envelope cause (hypothesis 1) and rules out an
  independent JSON/schema/target error for this response (hypotheses 2 and 4).
- Diagnostic tests reject malformed JSON, multiple fences, unmatched/plain fences, and
  leading or trailing prose. A fenced intent targeting completed `slot_1` remains rejected
  and leaves state unchanged. Thus the repair is full-envelope normalization, not substring
  extraction, and the host's target check remains authoritative.
- The separate `evidence/creative-retry-repaired-replay.json` is generated deterministically
  from the original receipt shape and current synthetic board. It shows `slot_1`'s completed
  receipt preserved, `slot_2` still failed, `slot_3` still pending, and a new pending
  attempt-2 child. The original `evidence/creative-retry-live.json` was not edited. This is
  not another model attempt or a paid call.
- ` .venv/bin/python -m unittest tests.test_creative_retry_probe -v ` passed 9/9 tests;
  generated replay JSON exactly matches the saved replay; `git diff --check` passed.

## Assessment

Hypothesis 1 is supported with high confidence for this receipt: one exact whole-response
Markdown fence was the only obstacle to applying the model's otherwise valid intent.
Hypothesis 2 is ruled out for the normalized content; hypothesis 4 is ruled out because the
fenced target passes host validation and state application; hypothesis 3 remains a general
failure mode but is blocked by the exact-envelope tests. Keep normalization opt-in and
syntax-only. Strict JSON decoding, exact intent fields, failed-target matching, collision
checks, and trusted state transition remain in force. The replay establishes parser
compatibility and state preservation only, not model reliability, visual quality, or image
generation.
