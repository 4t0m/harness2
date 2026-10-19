# First live improver failed to improve

Expected: model edits a legal policy based on current task and failed rollout. Actual: all3responses wrapped JSON in Markdown and reproduced planted flawed policy. Strict parser rejected each; loop completed and selector returned ok but all solver checks failed. Preserve evidence/improver-wiring-live.json.

Hypotheses and tests before changing behavior:
1. Formatting alone caused failure: replay exact-single-fence normalization and strict guidance validation; then run candidate against frozen training and heldout oracle. If policy remains invalid, this is not solely formatting.
2. Editor lacks explicit improvement objective: inspect actual system/user prompt construction and included rollout. Presence of failed host verdict but no instruction to diagnose/correct distinguishes objective omission from absent feedback.
3. Context lacks source-required gap: inspect task/rollout content. The source scene itself is intentionally excluded; if rollout contains only wrong proposal and generic discrepancy, model may lack authoritative value, though it can choose preservation policy without memorizing gap. Do not expose heldout to fix this.

Tests are saved-response replay and source/receipt inspection, no new paid calls. A scripted selector choosing a deliverable is not an independent quality judge.

## Findings

All three saved responses become valid guidance JSON after exact-single-fence normalization, but every replay still fails both training and heldout checks. Hypothesis1 as sole cause is ruled out. Rollout does contain host rejection of changed stop_gap; lack of all feedback is ruled out. The original source-requested value is absent, but the preservation policy does not require guessing it.

ActorImprover.call discards mission and its system prompt asks to edit a template/preserve facts without explicitly diagnosing the observed failure or improving the current policy. Thus lost improvement objective is an actionable design defect, not proof of model inability. Next intervention should restore bounded stage intent and explicit feedback-driven improvement, while retaining strict response validation and separate failure counts. Do not claim this fixes the problem until tested. Existing exact-fence repair alone is insufficient.

Trial spent3calls with1,109prompt+189completion tokens and provider-reported $0.000101478. All3edits rejected; adapted holdout failed. Framework completion and scripted selection ok do not signify task success.
