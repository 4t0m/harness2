# VRM verification test invocation

Expected verification tests to run; unittest instead reported ModuleNotFoundError for tests.test_vrm_async. No application test executed. Two hypotheses suffice for this narrow import failure: incorrect module name, or wrong package environment. Diagnostic: enumerate tracked VRM tests and invoke the exact discovered module in the same interpreter. An existing differently named module that imports successfully supports the first; failure of that exact module supports the second.

File enumeration found tests/test_vrm_async_verification.py, not test_vrm_async.py. Proceed with the actual module; no product code fix is indicated.

The exact module and two adjacent VRM suites passed: six tests. Wrong invocation name confirmed; interpreter/package environment ruled out for this failure.
