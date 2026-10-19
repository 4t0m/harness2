# Production dispatcher baseline

Question: can a compact model choose one legal next action from a production ledger without violating dependencies, approval requirements or retry limits? This is a task-selection baseline, not actual image generation.

Eight synthetic ledgers. Development IDs: mix-order-01, blocked-02, approval-03, retry-lineage-04. Holdout IDs: dependency-unlocked-05, two-runnable-06, nothing-left-07, human-approved-08. Freeze this split before model trials; future adaptation must not read holdout responses or derive its instructions from them. If parent has inspected all results for reporting, use a separate editor context restricted to dev receipts and create additional untouched families before claiming broad generalization.

Initial run: at most8Gemma26BA4B calls,256output token cap,20second socket/30second hard call cap. Compare strict acceptance and exact-single-fence repair on identical saved responses; no second call for formatting. Preserve every error. Evaluate all legal choices rather than one preferred ordering. Waiting when useful legal work exists is a failure, as is starting blocked work. Final acceptance also requires unchanged completed receipts/unaffected rows and a valid post-transition ledger.

No jobs are submitted to an image backend, no human approval is invented and no balance is spent on generation. Ledger approval fields are synthetic test inputs. Live deployment requires a separate authoritative approval source and idempotent dispatcher.

## Initial live result

Eight Gemma calls: seven strict passes; the blocked-02 development case proposed retrying a job already at its attempt cap. Host validation rejected it before any dispatch. Exact-fence replay did not change the outcomes. Four held-out cases passed, but this tiny single-pass sample is not a general reliability estimate. No external jobs were run. Totals: {'calls': 8, 'strict_pass': 7, 'prompt_tokens': 3016, 'completion_tokens': 150, 'reported_cost_usd': 0.000225455}
