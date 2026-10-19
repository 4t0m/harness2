# Actor staging renderer contract investigation

## Problem frame

Expected behavior: the renderer accepts the trusted compiler's six-second staging plan while preserving its actor identity order, mirrored screen roles and host-selected anchor location. The current renderer requires list index 0 to be world x=-0.85 and index 1 to be +0.85, and its +Y-facing camera may invert the compiler's screen-left/right convention. Its preflight checks joint centers but not mesh radii. Any mismatch could reject valid compiled plans, swap visible roles, or let cropped geometry render.

## Context reviewed

- `harness2/actor_staging.py` is the host compiler; it preserves `scene.actor_ids` in its actors list and computes x as anchor x plus/minus 0.85 m from each actor's requested side.
- The host compiler allows anchor x in [-1, 1], actor x up to 3 m, and separation at least 1.7 m. The model can mirror roles independently of actor list order.
- The renderer currently hardcodes x anchors by list index, points its camera from +Y, points facial features toward +Y, indexes cues by list order, and checks projected joint centers only.
- Full Blender execution is deferred while a parent model trial is active. The diagnostics in this pass will not import `bpy` or render.

## Competing hypotheses

1. **The fixed renderer anchors match every compiled plan.** This predicts every fixture's actor list positions are exactly [-0.85, +0.85] in that order. It is ruled out by any compiler output with nonzero anchor x or reversed roles/order.
2. **Actor list index is a stable visual left/right role.** This predicts the compiler sorts actors by side before returning them. It is ruled out if actors preserve scene identity order while a role reversal changes their x coordinates.
3. **The +Y camera preserves the compiler's screen ordering.** This predicts increasing world X projects to increasing normalized camera X. It is ruled out by projection-basis math or a Blender `world_to_camera_view` check showing the opposite ordering.
4. **Joint-center bounds are sufficient for full-figure framing.** This predicts all sphere/cylinder extents stay inside the same margins as their center points. It is ruled out by any center that passes while its bounding radius crosses the frame margin.

## Diagnostic plan

1. Without importing the renderer, compile all four existing staging fixtures and extract actor IDs/order, x coordinates, centroid, separation, and y/z. Confirm or rule out hypotheses 1 and 2 from the compiler outputs.
2. Parse only the renderer's `validate_plan` function AST and execute it with plain Python globals against those four compiled plans; record which plans it rejects and why. Do not import Blender or run the renderer.
3. Derive the camera screen-right vector from the camera's look direction and up vector. Confirm whether +Y viewing maps +world-X to left or right. Defer Blender-side projection tests until the parent model trial ends.
4. Implement preflight checks that accept the compiler's full static-placement contract, use explicit projected semantic ordering, and include marker/bone radii in camera bounds. Rerun the same four-plan isolated validator checks and syntax checks. Do not render.

## Findings

- Before repair, the isolated renderer validator accepted only `plinth_pair_intro` and rejected the other three fixtures because it tied actor-list order to `[-0.85, +0.85]`. The compiler preserves scene actor IDs and places each at anchor x ±0.85, so valid fixture x values include `[1.2, -0.5]`, `[-1.25, 0.45]`, and `[1.45, -0.25]`.
- The source confirms actor list order is identity order, while screen role is represented by x coordinate. The repaired validator accepts either order, enforces 1.7 m separation, pair center in [-1, 1], each x within 3 m, and y=z=0.
- Camera-basis calculation for a camera at +Y looking toward the scene gives screen-right proportional to -world-X. This reverses semantic left/right. Moving the camera to -Y gives screen-right +world-X; facial features now face -Y and nod pitches toward the camera. A Blender `world_to_camera_view` check remains deferred to the parent after the model trial.
- Projected preflight bounds now include sphere radii and bone radii in normalized x/y margins, plus a direct projected screen-order assertion. This logic passed syntax inspection but has not been executed inside Blender.
- The four compiler fixtures now all pass the isolated validator. `motion.json` keeps intended positions separately and records post-update joint object `matrix_world.translation` readback as `joints_world_m`. No renderer or model trial was run in this investigation.


Parent completed real Blender rendering after inference ended. Both initial and mirrored/offset model plans passed the updated dynamic projection/order checks and48frame readback validation; video decoding confirms48frames at8fps over6seconds. Protected-joint errors stay below1.15e-7m; segment-length error below1.16e-7m. The revised motion receipt records actual object matrix_world joint translations separately from intended formula positions. Parent decoded frames8/24/47 for both scenes; raised arm and neutral return are visible, while nod is subtle. Current evidence: actor-staging-render-v1.json and actor-staging-review-v1.json. No full human acting review.
