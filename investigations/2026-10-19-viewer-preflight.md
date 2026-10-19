# Viewer preflight review

Goal: truthful pending/queued/shutdown UI before the live trial. Review of the draft HTML found state.pending and queued_switch_ms are passed to a function as sample, where those fields do not exist; queued status also requires a pending request even though accepted queueing clears pending. No browser trial had run.

Diagnostic alternatives and checks: (1) The backend contract could put pending on sample: inspect the fixed runtime sample shape and agreed API; this would confirm a backend mismatch if fields were nested there. (2) The UI caller could pass the full state: inspect labelState call site; this would rule out lost metadata. (3) The UI could be mixing state levels: compare labelState(sample) with state.pending read elsewhere; contradictory paths confirm the UI mismatch. The existing runtime and HTML primary code support (3), not (1) or (2).

Additional direct review findings: undefined head-marker color; lifetime meter divides seconds by five despite a300-second session; shutdown is reported as finished before HTTP success and swallows errors. Request author correction before live execution: explicit state metadata, queued independent of pending, defined color, sensible remaining-time display, and truthful shutdown request/error states. These are reversible preflight corrections under the autonomous experiment authorization; no provider evidence or frozen runtime changes.

## Verified correction

The corrected HTML reads queued/pending state from the top-level API and displays queued independently of pending. The head color is defined; remaining lifetime is numeric; shutdown success reports only that shutdown was requested. Backend failed-call state stops exposing a misleading active pending request once the worker is no longer busy. Five offline HTTP tests pass. Subsequent actual browser trials showed queued, playing and stopped states, the source readback and a truthful shutdown acknowledgement. Parent process/port checks independently confirmed exit. Frozen source hashes and raw trial receipts are preserved in the motif-live evidence files.
