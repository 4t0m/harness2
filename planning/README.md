# Custom agents and small-model harness planning

This fork is our independent planning and experiment workspace for Google Research Harness². The existing Hermes lab continues its integrations and avatar work. Begin here, then read task-candidates.md and experiment-plan.md.

## Current capability status

Read [capability-status.md](capability-status.md) for the verified current state and unfinished milestones. Historical checkpoints below and in active-goal.md are not current deployment guarantees.

## Established setup

- Upstream: https://github.com/google-research/harness2
- Fork: https://github.com/4t0m/harness2
- Initial upstream revision: 1cfe254e8d25b15f37048c3730134686abe60335
- Planning branch: codex/local-agent-planning
- Python 3.12 virtual environment, minimal editable package installation.
- Upstream deterministic demo passed locally on macOS with k=1, both parallel and sequential modes: two tasks, zero failures, 14 executions and 16 scripted editor calls. This is not model inference.
- Upstream recommends Linux for full benchmark runs. Mac demo success does not establish portability of all benchmarks.

Run the lightweight demo in a fresh output directory:

```sh
.venv/bin/harness2-demo --output runs/my-demo --k 1
.venv/bin/python -m unittest discover -s tests -v
```

## What we are evaluating

Harness² adapts prompts, tool guidance, scripts, memory and orchestration around fixed model weights using propose–probe–compose loops and persistent evidence. We want to test whether that machinery improves a compact custom agent on real, checkable tasks, compared with a simple fixed harness and a bounded correction loop. It does not by itself supply avatar rigs, reliable local inference or a fine-tuning pipeline.

The first custom executor should expose typed, narrow tools and return durable receipts. A model proposes intent; trusted code resolves scene geometry, validates operations and verifies output. The model does not own the oracle or mutable copies of authoritative scene facts.

## First implementation target

Build a custom synthetic actor-planning adapter following the extension points in harness2/demo.py: task enumeration, source fixtures, base harness, execution and evidence. Use the same task oracle as the Hermes baseline. First run deterministic proposals, then a model-backed executor. Keep the evaluator outside editable harness trees. Do not shoehorn this into a legal or office benchmark just to reuse a runner.

An existing Mac Ollama endpoint has now been exercised with Qwen3 8B and 30B-A3B; see capability-status.md for measurements. No fine-tuned weights are configured. The future dual-5090 host is a deployment target, not a benchmark result. Provider routes must be checked for actual API compatibility; OpenAI-compatible chat completions and Responses API are not interchangeable.
