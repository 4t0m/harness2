# OpenRouter before RunPod

User explicitly authorized cheap OpenRouter trials before provisioning RunPod. Use the existing environment credential without copying it into this repository. Dedicated provider arguments pass that key only to the selected OpenRouter route.

Initial catalog check: qwen/qwen3.5-9b lists $0.10/M input and $0.15/M output; google/gemma-4-26b-a4b-it lists $0.0675/M input and $0.225/M output. These are advertised catalog prices at the check, not a guarantee of routed-provider billing. Source: https://openrouter.ai/api/v1/models . Recheck prices before a larger batch and record returned cost where available.

First probe: one synthetic actor JSON proposal per model, at most 512 output tokens each, 25-second socket timeout and a 90-second outer process alarm. Preserve raw content and finish reason even when empty, truncated or invalid. This is a provider/contract smoke test, not Harness² improvement evidence or avatar playback.

Next: frozen actor cases and art-manager plans with fixed harness, bounded correction, then adapted guidance; retain provider failures separately from task failures. Keep all inputs synthetic. Do not infer local GPU throughput or exact weight/quantization parity from hosted model behavior.
