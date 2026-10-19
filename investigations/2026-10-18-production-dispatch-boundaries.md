# Production dispatcher malformed operation and retry-ID boundaries

## Frame

Expected behavior: every malformed model action returns a structured rejection; every action
advertised by the host oracle must create a valid state. Review found a possible crash when
`operation` is an array or object, and a possible retry ID longer than the 40-character job
ID limit. A separate collision may also leave `valid_choices` advertising a retry that
`evaluate` then rejects. These matter before any live model call because the evaluator must
be total over untrusted JSON and its oracle choices must describe executable transitions.

## Context reviewed

- Current `_parse_action` checks operation membership in a set before checking the value's
  type. JSON arrays/objects are unhashable in Python.
- Current `valid_choices` checks retry cap and child lineage but not the host-derived retry
  identifier. `evaluate` appends `<failed_id>_retry_<attempt>` without truncation or a
  collision check until after the choice has been advertised.
- Retry IDs must satisfy the same `[a-z][a-z0-9_-]{0,39}` rule as all task job IDs.
- No fix or diagnostic test for these cases has been tried in this turn. The offline task
  fixtures and evidence are scripted; no provider is needed.

## Competing hypotheses

1. **Non-string operation crashes parsing.** A JSON array/object reaches set membership and
   raises `TypeError` rather than producing a structured rejection. Confirm by evaluating
   `{"operation":[],"job_id":null}` and `{}` operation; rule out if `evaluate` returns
   `valid=false` without raising.
2. **A maximum-length failed ID creates an invalid retry ID.** The suffix pushes the derived
   identifier beyond 40 characters, but the oracle still advertises retry. Confirm with a
   40-character valid failed ID and inspect the derived ID plus `validate_task(after)`; rule
   out if the oracle suppresses the action or the resulting state validates.
3. **A pre-existing unrelated job collides with the derived retry ID.** The retry may be
   advertised, then rejected during transition. Confirm with a legal task containing a
   distinct existing job whose ID equals the deterministic retry ID; rule out if choices
   omit retry or select a different collision-free ID.
4. **The retry transition violates another state invariant even after ID repair.** Validate
   each accepted retry result with `validate_task`; confirm if any accepted result fails
   lineage, attempt, receipt, dependency, or identifier checks; rule out across the focused
   fixtures if all accepted after-states validate.

## Diagnostic plan (written before tests)

1. Add evaluator tests using JSON arrays/objects as operation values. They must return
   structured rejection and leave the scene unchanged, never bubble `TypeError`.
2. Add a long-ID failed-job task and a retry-ID collision task. Assert `valid_choices` never
   includes an unusable retry; where retry remains available, its deterministic ID must meet
   the 40-character rule and be unique.
3. For every accepted retry case, call `validate_task(result["after"])`. Also test that an
   unrelated completed receipt remains unchanged.
4. Implement only input type guarding and one shared retry-ID derivation/availability helper
   used by both `valid_choices` and `evaluate`. Run
   `.venv/bin/python -m unittest tests.test_production_dispatch -v` and
   `git diff --check`. No API call.

## Findings

- The array/object operation probes raised uncaught `TypeError: unhashable type` in `_parse_action`.
- A 40-character valid failed-job ID produced a 48-character retry ID.
- A task containing a distinct existing job with the exact derived retry ID still advertised
  the retry choice. The transition would reject it after selection.
- These results support hypotheses 1–3. The retry after-state test also checks hypothesis 4
  by passing the applied state back through `validate_task`.

After the narrow fix, operation type checks return structured rejection for arrays and
objects. The shared retry-ID helper truncates the stem to keep the suffix within 40
characters and treats a colliding candidate as unavailable; `valid_choices` omits it.
Accepted transitions are validated again with `validate_task`. The long-ID retry succeeds
with a valid ID and a valid resulting state; the collision case returns no retry choice.
All 13 focused tests now pass and `git diff --check` is clean.

## Assessment

The parser and oracle defects were confirmed by reproductions at each hypothesized boundary.
The parser now type-checks before membership; both oracle and evaluator share deterministic
bounded-ID derivation, with collisions omitted from the legal set. All accepted after-states
are revalidated. Confidence is high for these four edge cases; no live or model-backed
behavior was tested, and none is needed for this contract repair.
