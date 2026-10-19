# Flat preview layout investigation

Expected: a readable complete flat proxy of the accepted motion. The first endpoint and six decoded video frames show the head separated from the neck stroke and labels overlapping the figure. Source motion and model success are not under revision.

Competing hypotheses and tests:
1. Source geometry/projection is inconsistent. Recompute head/neck/spine projection against saved local joints and world offset. Mismatches support this; identical coordinates with missing connecting drawing rule it out for the gap.
2. Renderer omits a connecting primitive. Inspect neck/head stroke endpoints and compare them to drawn head bounds. A positive pixel gap supports this; complete coverage rules it out.
3. Layout allocates insufficient top clearance. Compare minimum head pixels with header/progress/text bounds over81samples. Intersection supports this; disjoint bounds rule it out.

Plan: preserve v1 artifacts and source in Git; check coordinates and drawing commands; change only render framing/neck primitive and labels after confirming the cause; render a distinct v2 artifact; verify model-source hashes and compiled receipt unchanged, media dimensions/frame count, and inspect decoded output. Do not infer dance quality from the layout repair.
