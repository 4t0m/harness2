# First model-backed improver trial

Decision: can a bounded text-only proposer satisfy Harness²'s actual editing protocol while leaving task facts and acceptance outside model control? This is a wiring experiment, not a model-quality comparison.

Use ActorAdapter's deterministic solver with an intentionally flawed base policy, one left-mirror training task, k1 sequential recursion and a separate diagonal holdout. The editor may replace systemprompt.md only; valid coordinate and clearance policy enums are host-checked. Selector remains deterministic and experience returns NO_ENTRY. No persistent learned memory is claimed.

Budget: at most3 live Gemma26BA4B edit calls, bounded context and512output tokens each,25second socket budget with an outer150second process limit. No solver model calls, renderer or GPU rental. Preserve malformed/incomplete proposals; do not silently repair until a separate intervention is declared. If pipeline asks for additional calls beyond cap, fail explicitly and retain partial evidence.

Report edited text, provider usage/latency/cost where returned, host validation, actual loop stage ledger and heldout verdict. A successful result proves that real model edits can flow through the pipeline. The base's planted fault and scripted executor prevent interpreting any resulting improvement as real-agent adaptation benefit. Later use naturally failed nontrivial tasks for fixed/repair/adapted comparison, with untouched task-family holdouts.
