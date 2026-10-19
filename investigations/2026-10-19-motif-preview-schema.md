# Motif preview schema preflight

## Goal and observed issue

The preview must select only completed, brief-correct compact responses from the local Qwen 3 8B calls, independently recompile them, and preserve the compiler receipt and source provenance. Parent review identified a mismatch between the renderer's assumed call fields and the live probe's actual report schema. No rendering failure has occurred; the renderer has not been run against model evidence.

The renderer before this correction had SHA-256 `6e64f7b0d39dc1e90251e935b4cad99062942c1e2a8944a0f3f7069ae4a1a21e`.

## Hypotheses and discriminating checks

1. **Stale call-field assumptions.** The renderer may expect names from an earlier probe. Inspect the current call-row writer and compare its fields with selection and receipt handling. This is confirmed if field names or required values differ; ruled out if the exact names and semantics match.
2. **Selection can admit the wrong representation or provider.** The selector may choose expanded output or a hosted row. Inspect the call construction loops and verify the selector filters both `condition` and exact local model identity. This is confirmed if those dimensions are omitted; ruled out if the filter excludes both row classes.
3. **Compiler or report provenance assumptions drifted.** The renderer may expect incorrect frame metadata, section labels, or saved receipt fields. Inspect `compile_intent`/`verify_score`, their tests, and the probe's saved call/report fields. This is confirmed if those differ from renderer assertions; ruled out if the compiler and report agree.

## Checks and findings

- The live probe writes call rows with `condition`, `compiled`, `brief_correct`, and `finish_reason`; it stores the verified compiler receipt as `motion_receipt`. The old selector instead checked `correct` and treated a generic `receipt`/`score_receipt` as optional. Hypothesis 1 is confirmed by the probe's row construction and result-update code in `experiments/dance_motif_probe.py`.
- The probe interleaves compact and expanded conditions across four local and two hosted models. Filtering only by model and case would admit an expanded row; filtering exact model without condition could still select that model's expanded row. Hypothesis 2 is confirmed. The corrected selector requires the exact local Qwen model, `condition == "compact"`, `compiled is True`, `finish_reason == "stop"`, and `brief_correct is True`.
- The probe invokes `compile_intent`/`verify_score` for compact calls and records the resulting `intent` and `motion_receipt`. The compiler constructs A,A,B,A sections, 321 frames at 20 fps, 32 beats, and 16 seconds; `verify_score` rebuilds and checks the canonical receipt. Hypothesis 3's prior receipt-field assumption was confirmed; its frame/label assumptions match current compiler metadata. The corrected renderer recompiles the raw content and compares both saved intent and `motion_receipt`.
- Probe `sources` are hashes for the motif compiler, phrase compiler, motion source, bounded HTTP adapter, fixture, and probe itself. The renderer checks each supplied source hash before selection. This preserves the live trial's frozen provenance; the renderer records the input report hash and its own renderer/compiler/fixture hashes separately.
- The renderer checks the verified score's 321 samples, 20 fps, 32 beats, 16-second duration, and A,A,B,A labels. Its video probe expects 800x420, 20 fps, 320 encoded frames, and 16 seconds, while the 321st terminal sample is emitted as a separate PNG. These are format checks only; no visual-quality claim follows.
- `tests/test_dance_motif_score.py` covers all 32 compact scores against expanded compilation, verifies 321 frames and 20/32/16-second metadata, and tests seam/receipt rejection. The bundled Python test run completed 4 tests successfully. The renderer itself was syntax-parsed only and remains unexecuted.

## Conclusion

The mismatch was a stale renderer schema assumption, not evidence of a failed render or an inference failure. The source-level checks distinguish that from accidental expanded/hosted selection and from compiler metadata drift. The renderer now follows the probe's actual compact local-call fields and receipt names. It remains unexecuted until the parent confirms the evidence report is complete.

## Projection-layout preflight

Parent review identified a possible collision between the head and panel labels before the first renderer execution. No render has run. Three layout hypotheses require a joint-track check:

1. **Head overlaps title/detail text.** Project every head sample for both motif directions and compare its drawn hair/ellipse extent with the lowest title/detail label bound. The new layout passes if the minimum head top is below (greater y than) the label bottom with a positive gap; fails otherwise.
2. **Limbs or clothing clip the character panel.** Project every joint for all 321 samples, both motifs, and all 16 accent patterns; include limb line width and head embellishment margins. The layout passes if all drawn geometry stays within the panel rectangle; fails if any expanded bound crosses it.
3. **Feet or ground marker collide with the panel footer.** Compare lowest projected foot/limb extent and root marker bounds with the panel bottom. The layout passes if both retain positive footer clearance; fails if either reaches/passes the panel edge.

The planned diagnostic is an in-memory compiler enumeration over the fixed 32 intents (two motifs x sixteen accent vectors), checking all 321 samples each, with explicit tests for header/detail separation, panel margins, and footer clearance. The renderer remains unexecuted; this geometry-only check does not create frames or media.

### Projection-layout results

The old 800x420, baseline-360 layout did have a head/text collision: at 138 px/m the head center projects to about y=125, with the hair top extending to y=105 while detail text occupies y=141. The renderer was changed to 800x520, baseline y=460, 160 px/m, panel bottom y=500, and ground marker y=485..493; the ffprobe expectation now checks 800x520.

The in-memory diagnostic compiled both motifs with all 16 accent vectors and passed the renderer's projection-bound helper for every sample: 32 intents and 10,272 actor-samples total (321 per actor per intent, both panels). Minimum clearances were 9 px from head and all projected art to the detail-label band, 7 px from expanded geometry/marker to panel edge, and 27 px from the feet to the ground marker. These checks cover projected joint/figure bounds and UI rectangles, not rasterized glyph anti-aliasing or visual taste. No renderer, frames, video, provider, or model call was run.

## Rendered redundant label clipping

Parent inspected source frames 30 and 190 after the first render: the redundant SECTION label below the AABA bar was partly hidden. Three explanations were checked: text drawn behind the panel, font rasterization alone, or video encoding. Source PNGs already show clipping, ruling out encoding. The renderer draws SECTION at y=104 and then a filled panel from y=111; the label extends into that panel. Other labels with the same font draw correctly. Drawing order and overlapping bounds explain this display defect. Remove the redundant label, retain the original renderer at commit 4188aa3 and all v1 media/evidence, and render separately as v2. No model or movement data changes.
