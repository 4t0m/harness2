# Preserving accepted motion around a local edit

Host-authored capability proof, no new model inference. Starting from the actual prior model-selected wave scene, reduce right-shoulder Y rotation at keyframe24 from 2.72 to 2.35 radians. Linear neighboring keys at12 and36 constrain the effect to frames13–35. Save a separate revised.blend; original SHA-256 remains unchanged.

Verification: all object world matrices compared at each of48frames (rounded to7decimalplaces). Every object is unchanged outside13–35. Non-arm objects are unchanged at all48frames. Only the shoulder and descendants change. This is transform preservation, not a complete materials/mesh/physics audit.

The first rendering attempt crashed after generating the alleged original preview. Later byte comparisons exposed that preview as identical to revised: mutating curves after rendering in one process was not a trustworthy baseline. See investigations/2026-10-19-blender-span-render-crash.md. Recovery used immutable scenes in fresh Blender processes. The original-isolated and revised-isolated decoded RGB frames match outside the edit and differ inside it at every sampled frame. Visual inspection confirms a lowered mid-gesture arm.

Verified comparison assets in `/Users/adom/Development/hermes-testing/runs/harness2-span-preview-v1/`:
- `original-isolated.mp4` is the corrected baseline; do NOT use `original.mp4`.
- `revised.mp4` is the verified revised preview.
- `revised.blend` is the editable result.

Each preview is2seconds,320x320,6fps (12samples from the48-frame scene),1EEVEE sample. Low sample count visibly adds noise; sparse playback is not smoothness or final-quality evidence. No claim of dance biomechanics or taste improvement. This proves a narrow editing primitive suitable for eventual typed model control: modify one bounded parameter while preserving neighboring motion. Model-generated edits and human preference evaluation remain future work.
