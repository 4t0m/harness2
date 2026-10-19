# OpenRouter Qwen chat response investigation

## Problem and current evidence

Expected: a single `qwen/qwen3.5-9b` chat-completions call returns a classified proposal response, including content, finish reason, usage, and served model. Observed: `runs/openrouter-smoke/results.json` records `ProviderError: malformed provider response`; the original raw response was not retained. The same smoke's Gemma response parsed and yielded a valid synthetic actor proposal. This matters because provider failures must remain distinct from task failures before comparative trials.

The current parser requires one choice, string `message.content`, nonempty string `finish_reason` and `model`, and three integer usage fields if usage exists. Git history shows this parser was added in `08cd762`. `planning/openrouter-first.md` specified 512 output tokens, a 25-second socket timeout, and a 90-second outer alarm, but the saved result does not show which check failed.

## Hypotheses and discriminating tests

1. **Reasoning consumed the token cap.** Qwen may return `message.content: null` or empty while placing text in a reasoning field, with `finish_reason: length`. Capture one raw response before parsing to an ignored `runs/openrouter-smoke/diagnostic-qwen-1.json` file. Inspect only field names/types, finish reason, usage integers, content length, and reasoning length. A null/empty content with `length` and near-512 completion tokens supports this; normal nonempty content and `stop` rules it out for that response.
2. **Envelope differs from our narrow parser.** Qwen's route may omit/alter `model`, `choices`, `finish_reason`, or usage fields while still returning a 200 JSON response. Inspect the same captured envelope's top-level and choice/message key names and field types without printing content. A valid JSON object with a missing or differently typed required field, independent of token exhaustion, supports this. A complete expected envelope rules it out.
3. **Provider returned an error payload or routing refusal in HTTP 200.** Inspect top-level `error`/`message` types and choice count in the capture. A top-level error object with no valid choice supports this; a choice with a model and finish reason rules it out.
4. **Malformed transport bytes or our parser bug.** Check byte length, UTF-8/JSON decode status, duplicate keys, and replay the captured bytes through `_parse_response`; compare the first failed condition. Invalid JSON/oversize supports transport/body failure. A parser rejection despite an otherwise valid expected envelope points to our overly strict parser.

## Procedure and limits

First check that `OPENROUTER_API_KEY` exists without printing it. Use only `https://openrouter.ai/api/v1`, model `qwen/qwen3.5-9b`, and a synthetic actor fixture. A Python wrapper calls the existing `chat_completion` with an injected transport that delegates to `_default_transport` and writes returned bytes with owner-only file permissions before parsing. Do not log the request, credential, content, or reasoning text. For each diagnostic request: `max_output_tokens=512`, socket timeout 25 seconds, process alarm 90 seconds. At most two requests. After request one, analyze the capture locally; make request two only if it distinguishes a remaining ambiguity. Record capture path, redacted field/type summary, parser outcome, and conclusions here. Do not treat truncated or missing content as a successful task proposal.

## Diagnostic results

`OPENROUTER_API_KEY` was present. The first sandboxed attempt could not connect and sent no request. Two authorized network calls then completed to the specified OpenRouter route, with raw responses saved as owner-only files under the ignored run directory. Neither response body nor reasoning text was printed.

| Call | Capture | Parser | Content | Finish | Completion/reasoning tokens | Envelope |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `runs/openrouter-smoke/diagnostic-qwen-1.json` | parsed | string, 186 chars | `stop` | 455 / 376 | one choice, expected model and usage fields |
| 2 | `runs/openrouter-smoke/diagnostic-qwen-2.json` | malformed response | null | `length` | 512 / 512 | one choice, expected model and usage fields |

Both responses were valid JSON and below the 1 MiB cap (3,757 and 5,141 bytes). Call 2 spent the full allowance on reasoning and returned no final content. This reproduces the generic parser failure and strongly supports hypothesis 1 as a mechanism. It rules out a consistently different envelope, a provider error payload, invalid JSON, and oversize bytes for these calls. It does not prove the uncaptured original response had this same shape; that remains unknown.

## Assessment and chosen fix

Confidence is high that a reasoning-only `length` response causes this client failure, and moderate that it caused the original smoke failure. Classify `length` as an incomplete completion even when partial text exists; classify null/empty content with other finish reasons as missing content. Keep these out of successful task proposals. Expose finish reason, model, usage, latency, and optional raw response on a typed exception so the caller can preserve a diagnostic receipt without automatically logging private reasoning. Keep truly malformed envelopes and provider error payloads distinct. Add offline tests for the reproduced shape, partial truncation, missing content, and error envelope. No more live requests are needed for this fix.
