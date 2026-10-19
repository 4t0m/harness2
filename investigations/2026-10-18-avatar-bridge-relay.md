# Avatar bridge cannot reach relay

Expected: accepted intent reaches the existing flat relay, then resets neutral. Actual: worker URLError, neither delivery nor cleanup confirmed. No action confirmed. This is first live bridge attempt; previous browser screenshot proved pixels only.

Hypotheses and diagnostics, before retry:
1. Relay stopped: inspect TCP listeners and attempt read-only configured state endpoint. Connection refusal with no listener supports this; successful state rules it out.
2. Minimal worker environment selects wrong default URL: inspect adapter URL configuration and compare known8000 browser URL. Different control/state port/path supports mismatch; matching configuration rules it out.
3. Relay reachable but required endpoint unavailable: read configured endpoint HTTP status. HTTP error with live listener supports endpoint mismatch; connection refusal instead rules it out.

Preserve original runs/live-avatar/receipt.json. Do not restart a service until identifying its owner, command and current terminal process state. If starting a stopped independent test relay is appropriate, retain a live process handle and clean up only that owned process.

## Diagnostic findings

Adapter uses hardcoded http://127.0.0.1:8000, matching browser origin; minimal environment does not select a different URL. No TCP listener on8000 or8001 was found. The live worker immediately returned URLError. These observations support stopped relay, not HTTP endpoint mismatch. Existing source README documents python obs_server.py; source is in sibling hermes-testing runs/round5/anime-source. Browser cached pixels do not establish server health. User steered to experiment-space planning before any restart; service restoration remains next work. No new process was started.

## Restored relay trial

Rechecked port8000: no listener. Started existing obs_server.py on127.0.0.1 with no camera/open-browser flags, owned exec session55067. Replayed an independently accepted saved Gemma intent; no paid model call. Delivery, readback and neutral cleanup all confirmed. Original failure remains preserved; evidence/avatar-bridge-live.json contains public-safe statuses. This intervention supports stopped relay as the connection failure cause.

Screenshot timestamp03:48:21UTC falls within the three-second hold (03:48:20.558–03:48:23.566). Avatar rendered during and after, but requested gaze direction was not independently isolated from idle motion; do not claim pixel-verified look-right. Local screenshots in sibling hermes-testing/runs/harness2-live-avatar. Next visual experiment needs a stable baseline or an explicitly measured eye-region comparison, not repeated full screenshots without a discriminating hypothesis.
