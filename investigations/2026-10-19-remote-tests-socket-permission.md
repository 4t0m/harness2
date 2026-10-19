# Remote viewer offline test permission check

Parent rerun of the remote/viewer/HTTP tests used the default restricted sandbox. Five remote tests passed, while five viewer setups and the HTTP suite setup failed at `socket.bind(('127.0.0.1',0))` with `PermissionError: [Errno 1] Operation not permitted`. No provider request or model call was made.

The investigate skill applies. Context: Sol's same-source tests had passed with local listener permission. Only one causal hypothesis is needed here because the exact failing syscall explicitly denies bind permission before any handler or transport executes; address collision would be EADDRINUSE, while provider logic cannot run before fixture construction. Discriminating check: rerun the exact suite with approved loopback/network permission and unchanged sources. Success supports environment restriction; the same failure would require checking OS listener permissions. Do not change application code to mask a fixture permission failure.

Unchanged-source rerun with approved loopback permission: 15 tests passed in 5.586 seconds. The restriction was the cause; no application fix was needed.

A second parent invocation exposed a test-runner dependency mismatch: the gate tests originally imported pytest, which is absent from the minimal project virtual environment. Import failed before any test execution. Sol converted those same five cases to stdlib unittest; `.venv/bin/python -m unittest tests.test_motif_pod_gate -v` then passed all five in 2.591 seconds. No dependency install or gate behavior change was required for this runner correction.
