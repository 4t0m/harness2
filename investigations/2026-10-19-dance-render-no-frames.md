# Missing procedural dance frames

First prototype validation passed for both variants; Blender returned process status zero, but ffmpeg found no PNGs. Hypotheses: script raised a Python exception while Blender returned zero; frame paths differ from encoder expectation; renderer initialization failed. First inspect preserved render.log and output inventory. Trace any exception to exact source before editing; inspect JSON schema if the exception refers to data. Use a fresh output/evidence version for a repaired run, preserve v1 and tracks hash.

The preserved Blender traceback is KeyError metadata at bone_edges access. Generated tracks store bone_edges at top level. Thus this was a producer/consumer schema mismatch, not failed GPU initialization or a filename issue. Fix the renderer's access and request nonzero Blender exit on Python errors; rerun as v2 to preserve v1.

Fresh v2 rendered 40 PNGs and a verified four-second 512x320 video in 4.25 seconds. The tracks hash exactly matches v1, so motion source was unchanged by the renderer repair. Sparse decoded frames visually confirm both rigs and variant differences.
