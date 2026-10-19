# Live flat-avatar viewer experiment

## Purpose and predeclared scope

Move the checked motif playback contract into an actual browser display, while local inference runs asynchronously. This extends the finite after-rendered recording with a live polling/rendering path. It retains the existing motion/compiler, and does not change Hermes-owned driver, DATA, avatar services, or character identity. The existing Hermes bridge only offers look_right/neutral; it cannot carry full motif joint samples. A separate short-lived loopback viewer is therefore the appropriate test surface.

The Python host owns request IDs, time, deadlines, queued replacement, stop and raw evidence. The browser draws host samples and offers direction/stop controls. Models submit compact intent only. No renderer code, clocks, endpoint URLs, or host checks are model-editable. The original runtime still refuses a restart from a frozen non-rest pose rather than silently teleporting to rest.

## Bounded trial

Start a fresh finite viewer session with an explicitly selected installed local model, a new evidence path and an automatic lifetime limit. At most six local calls per session, one in flight, 20 seconds per request, 128 output tokens and 4096 context. No cloud calls, downloads, persistent services or system changes. Stop is processed independently of inference. Raw model output is saved outside the browser. Loopback-only binding and strict same-origin JSON POSTs protect mutation routes.

Open the page in the browser and verify that it polls and visibly draws the current host pose. Request an initial score, a replacement and a third score that is interrupted while inference is pending. Preserve real completion timings; do not synthesize stale replies. Independently replay accepted scores and served samples, then inspect browser readback and actual screenshots. A screenshot establishes a visible instant; server responses alone do not prove continuous browser motion or frame rate. Record UI access and backend admission separately.

The live service is intentionally short-lived. End the experiment explicitly and verify process exit and closed listener. Reopening the saved HTML without the service is not a working live deployment. Any future persistent integration remains a separate step.

## Local model identity at preflight

Ollama returned both installed model tags before trial startup:

- `hermes-lab-qwen3-8b:latest`: digest `ce2f25b8da1b2f736433c5d436bb28c61751bcc4710c6f13697e05170b685552`, stored bytes 5,225,388,180.
- `gemma4:e2b`: digest `7fbdbf8f5e45a75bb122155ed546e765b4d9c53a1285f62fd9f506baa1c5a47e`, stored bytes 7,162,405,886.

Tag metadata identifies this Mac's installed packages; stored size is not active parameter count, VRAM demand or a throughput benchmark.

## Observed result

The live browser now draws poses from the running host controller. Sol implemented the bounded HTTP host and five focused offline tests; Luna implemented the self-contained SVG viewer. Both sources were frozen before live calls. The original runtime/compiler were preserved.

Two matched three-call trials used real local Qwen3 8B and Gemma4 E2B. All six replies matched the requested intents. Both replacement scores became active at the first four-second boundary. Both third inferences started before stop and completed after it; their deliveries were rejected as stale. Qwen stopped at5.250seconds of playback, E2B at5.193seconds. Their late deliveries arrived1.100 and1.068seconds after stop. Initial provider calls took2.241 and3.311seconds; subsequent calls took0.900–0.931seconds. Preparation took0.284–0.300seconds. These are single-session observations with loading effects, not a throughput ranking.

The parent independently reconstructed all1,248 Qwen and629 E2B served frame hashes from raw scores and event timestamps. These logs include both browser polls and trial-driver reads; they do not measure the browser's displayed frame rate. Actual browser screenshots show queued and stopped states, and expanded visible readbacks match the stopped source pose and stale-delivery events. The matched trial's direction and stop requests came through timed HTTP orchestration. Shutdown was clicked in the browser.

A separate one-call Qwen session tested the visible Direction, Stop and End session controls through CUA. The entered pulse/soft-clear-soft-clear direction was accepted correctly, the page visibly entered motion, and Stop froze the pose at source time8.5seconds. Its378 served frame hashes and visible readback also replay. Across all three sessions: seven local calls, seven matching briefs, 1,463 native input tokens and185 output tokens. Initial contexts ranged207–210tokens; outputs23–29tokens. No hosted charges; local hardware/electricity cost unmeasured. These simple within-library briefs test live integration, not general language reliability or an H2 learning gain.

All three processes exited after browser shutdown, their inference workers drained, and independent loopback connections returned connection-refused. No server is intentionally left running. Screenshots/readbacks live in `/Users/adom/Development/hermes-testing/runs/harness2-motif-live-v1`; `ui-playing.png` shows the page-button trial. The image is an actual browser screenshot rather than an offline animation render.

## Reproduction and evidence

From this repository, launch a fresh finite session with a new output filename:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m harness2.motif_viewer --model hermes-lab-qwen3-8b:latest --output /private/tmp/motif-viewer-new-session.json --lifetime 300
```

Open the exact loopback URL printed at startup. Enter a brief specifying sway or pulse and four soft/clear accents. A playing replacement waits for a shared rest boundary. Stop holds the current pose; restarting from an arbitrary frozen pose remains unsupported. End session requests server shutdown; process/port verification remains separate from the page's acknowledgement.

- `evidence/motif-live-{qwen,e2b}-server-v1.json`: source hashes, raw model replies, events, served-frame hashes and termination.
- `evidence/motif-live-{qwen,e2b}-trial-v1.json`: timed API orchestration and returned full samples.
- `evidence/motif-live-{qwen,e2b}-check-v1.json`: independent compiler/timestamp replay.
- `evidence/motif-live-ui-controls-server-v1.json`: separate actual browser-button trial.
- `evidence/motif-live-ui-check-v1.json`: visible readback checks, screenshot hashes and closed-listener checks.

## Remaining gaps

This is a finite live technical proxy, not a persistent Hermes service or completed anime rig. No continuous displayed-frame-rate, audiovisual synchronization, natural-language stop detection, smooth recovery from an arbitrary pose, varied dance style, or subjective taste result is established. The useful next step is to expose explicit recovery options and richer verified motion through the same live control surface; repeated simple successes alone would add little evidence.
