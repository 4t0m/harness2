# Flat preview layout investigation

Expected: a readable complete flat proxy of the accepted motion. The first endpoint and six decoded video frames show the head separated from the neck stroke and labels overlapping the figure. Source motion and model success are not under revision.

Competing hypotheses and tests:
1. Source geometry/projection is inconsistent. Recompute head/neck/spine projection against saved local joints and world offset. Mismatches support this; identical coordinates with missing connecting drawing rule it out for the gap.
2. Renderer omits a connecting primitive. Inspect neck/head stroke endpoints and compare them to drawn head bounds. A positive pixel gap supports this; complete coverage rules it out.
3. Layout allocates insufficient top clearance. Compare minimum head pixels with header/progress/text bounds over81samples. Intersection supports this; disjoint bounds rule it out.

Plan: preserve v1 artifacts and source in Git; check coordinates and drawing commands; change only render framing/neck primitive and labels after confirming the cause; render a distinct v2 artifact; verify model-source hashes and compiled receipt unchanged, media dimensions/frame count, and inspect decoded output. Do not infer dance quality from the layout repair.

Checks: all81×18 logged joint projections exactly match independent projection from recompiled motion. Source geometry/projection mismatch is ruled out here. The endpoint head center is(356,64), its drawn lower edge82; the neck stroke begins at y95, leaving a13pixel gap. The hair top spans y41–44 across frames, overlapping the header/progress region. Source inspection confirms the neck primitive began at neck rather than connecting to the head; the long caption also crosses the actor region.

Chosen repair: retain v1 and its source at commit c293f2e; reduce scale180→160pixels/metre for clearance, connect head to shoulder neckline, remove the technical subtitle, and place the target label beside its line. Save v2 separately. This changes the illustrative drawing only, not the compiler, tasks or model evidence.

Verification: v2 retains exactly the v1 compiled receipt and selected repaired model attempt. Independently reprojected all81×18joints and checked actual saved PNG root-marker center pixels for all81samples. Every head clears the progress bar. Video/endpoint hashes and80frame20fps4second metadata match. Parent inspected endpoint and decoded frames0,10,30,50,70,79: the neck gap and text collision are resolved. These are presentation fixes; model reliability and physical limits remain unchanged.
