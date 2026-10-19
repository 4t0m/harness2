# Staging H2 editor wrapper failure

## Frame and context

Actual run v1 made one local development call, then two hosted-wrapper calls failed immediately with ValueError and zero reported spend. Framework finished partial with no final candidate. Offline injected-provider tests passed; they do not exercise network deadline wrappers. Preserve v1 evidence and run directory. The new runner installed a process signal timer around hosted requests; the earlier local helper also uses signals. The actual H2 scheduler may execute provider work from worker threads even in sequential mode.

## Hypotheses and diagnostic plan

1. Signal installation from worker threads fails before HTTP. Run an isolated ThreadPoolExecutor call to signal.signal and record the exception; inspect core recursion provider call scheduling. A main-thread-only ValueError and worker scheduling supports this; execution on the main thread or successful signal setup would rule it out.
2. Provider payload/metadata/key conversion raises before dispatch. Inspect the exact block before request creation and preflight JSON encoding using dummy credentials, without HTTP. Successful encoding and existing string credential rule out these local construction errors, but cannot validate server support.
3. Provider or response parser rejects the real request. Inspect raw_response presence, timings, and HTTP/error fields. No raw response plus failure before request creation rules out response parsing for that call; an actual response/error would require separate network investigation.

Choose a thread-safe bounded transport after the tests. Prefer a subprocess transport with an explicit wall deadline and kill on expiry, rather than unenforced thread timeouts or shared process signals. Keep model/call/cost caps and retry only in a fresh version after preserving v1.

## Findings and chosen repair

An isolated ThreadPoolExecutor invocation raised `ValueError: signal only works in main thread of the main interpreter`. Core recursion uses ThreadPoolExecutor for proposer phases even with sequential recursion. Both failed hosted rows have no raw response and elapsed times under 0.00004 seconds; the first hosted statement after payload construction installs that signal. The payload encodes successfully. This identifies pre-HTTP signal installation as the immediate failure; server JSON/schema support remains untested by v1.

Use a subprocess with a real wall timeout for every provider call, including local inference that could also run in H2 workers. Serialize provider calls with a lock so call limits, cost accounting, report writes, and local compute do not race. Preserve v1 source alongside this investigation and write new evidence/run directories as v2. This changes transport/concurrency handling, not the task, model schemas, or evaluation answers. Offline helper tests and a fresh actual run are still required.

## Verified outcome

The new subprocess helper passed five offline localhost tests, including actual worker-thread invocation, child-only bearer lookup, total-deadline expiry, oversized/malformed responses, redirects and error redaction. Four adapter integration tests also pass. Fresh v2 completed the actual H2 recursion and all evaluation conditions: 48 calls, including three successful hosted editor requests. Source hashes match the executed files; evaluation hash matches v1. The failed v1 and its exact runner remain preserved. Total wall limits apply to the request subprocess, not a claim that a remote provider cancels its own computation when the client exits.
