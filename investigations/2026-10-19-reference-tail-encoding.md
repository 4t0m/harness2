# Reference tail encoding

Expected: 96 render frames plus11identical final-pose frames decode to107frames, and tail frames95..106 match. First new reference probe rendered successfully but decoded-tail hash equality failed. This exact gate matters because padding should add a hold, not changed motion. No prior fix. Current topic has no earlier encoding changes; baseline GLB/bundle commits are unchanged.

Hypotheses and distinguishing tests:
1. Wrong input count or padding offset. Count PNGs and ffprobe output, inspect raw filter output hashes. A count other than96/107 or wrong raw final-hold start supports this; correct counts and12identical final raw frames rule it out.
2. The tpad clone operation changes image data. Run the identical PNG/tpad filter directly to raw framemd5 without lossy encoding. Different raw tail hashes support this; identical hashes rule it out.
3. Default lossy H264 reconstruction differs across repeated source frames. Compare raw filter tail hashes with decoded current H264 hashes, then encode the same input/filter with lossless H264 settings into a separate diagnostic file. Stable raw and lossless decoded tails but differing default decoded tails support this. If all differ, encoding alone is insufficient.

Do not weaken equality before distinguishing these. Use the preserved v1 frame folder/video, no render rerun for diagnosis. Record primary count/hash evidence. Avoid claiming pixel equality with RGB source if using lossless coding after YUV conversion.

Primary diagnostic:96PNGs; raw filtered output107frames with1unique hash over frames95..106; default H264107frames with11unique tail hashes; lossless H264107frames with1unique tail hash. Counts/padding are correct; lossy reconstruction caused the failed equality gate. Use crf0 for the reference master while retaining yuv420p conversion; this preserves repeated decoded frames, not RGB source pixel identity. Diagnostic receipt remains in v1/tail-diagnostic.json; failed v1 remains immutable. Fresh v2 will keep the exact gate.
