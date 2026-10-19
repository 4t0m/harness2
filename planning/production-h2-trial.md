# Production planning through Harness²

Prepare a model-backed production solver and a provider-backed guidance editor using actual run_domain, sequential k=1. Development uses original blocked-02 only for the initial bounded wiring run. Freeze the four combination cases in experiments/production_holdouts.py before live calls: alternate useful work beside an exhausted job, retry lineage with remaining capacity, approval plus blocked dependencies, and a successful retry unlocking an approved dependent.

The editor may see only the development task, current guidance and bounded development rollouts. Evaluation tasks must not be installed into its adapter/source tree or provided to the editor. Instantiate a separate evaluation adapter after guidance is frozen. Host evaluator, task ledger, approval and receipts remain outside editable guidance. The model produces data, not executable code.

One public rule must be included equally in baseline and adapted solver instructions: a completed retry descendant satisfies a dependency on its failed ancestor. This is oracle semantics, not the correct answer to a particular case. Without that shared rule, evaluation of successful-retry dependencies would test an undocumented contract.

Report fixed, fixed-plus-one-correction, and adapted strict outcomes separately. Scripted k=1 selection and memory omission must remain labelled. One development task cannot teach every semantic combination; negative transfer is a useful result. Preserve model responses, calls, input/output tokens, latency and reported cost. Framework status is not task success. Do not claim a general gain from one small batch.

Before a live run: verify adapter tests and total budgets; default at most three editor calls, bounded solver calls, 256 solver output tokens and 512 editor output tokens. Do not replay completed trials or overwrite receipts. A fresh run needs a unique output directory and retains partial records on timeouts. No real image/animation jobs are dispatched.

Runner prepared: experiments/production_h2_probe.py. Global hard cap 24 provider calls, including up to 8 development solver calls and 3 editor calls; four evaluation cases each allow one fixed proposal, one conditional fixed correction and one adapted proposal. A single wrapper enforces 30-second per-call deadlines and saves calls before dispatch and after return. Selection success does not imply an improved harness; report guidance and independent host verdicts. No live execution has occurred at preparation time.

## First live run: completed, no adaptation accepted

18 calls, 18,527 input tokens, 702 output tokens, provider-reported $0.001600206. Actual run_domain finished. Three editor calls were rejected for strict JSON format; therefore the selected guidance equalled baseline. Development decisions varied despite unchanged guidance (base/composed failed; domain/invariant executions passed).

Combination evaluation: fixed first pass 1/4; fixed with one correction 1/4; the condition labelled adapted 2/4. **The last condition used unchanged guidance and is a repeat, not an adaptation gain.** In particular, exact retry-cap feedback did not help failures involving useful alternative work or retry ancestry because those cases received generic feedback. Do not generalize the prior 4/4 near-transfer result to these combinations.

A syntax-only offline follow-up confirmed all three editor proposals become valid after exact-single-fence removal and a host-added final newline. Parser updated and tested; no fresh provider loop yet. Preserved both failed fence-only replay and successful canonical-format replay. Future trials must retain the changed-guidance flag and editor receipts before interpreting any solver differences.
