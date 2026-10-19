# Dance motion rig geometry investigation

## Problem frame

Expected behavior: every declared skeletal edge keeps its authored length unless an explicit articulated transform is represented. A foot marker should follow the ankle as one rigid foot in this prototype; a pelvis bob should translate the connected torso and hips consistently. The current output keeps foot marker z fixed while the ankle lifts, keeps hip/spine/head z fixed while pelvis bobs, and omits ankle-to-foot edges. This matters because the parent renderer consumes these joint positions as one stick rig, so the current output may visibly deform despite passing limb-only length checks.

## Context reviewed

- The D1 motion prototype was committed as `16b0353` (`Render first procedural full-body motion variants with contact checks`).
- The relevant code sets foot marker to `[ankle.x, ankle.y + 0.10, 0.055]` unconditionally, generates ankle z from a swing arc, and declares no ankle-foot edge.
- Pelvis z varies by beat, while hip, spine, neck, head and shoulder z values are constants. The top-level bone edge metadata connects these nodes.
- Existing validator checks leg and arm lengths, but not torso, hip, shoulder attachment or foot-marker segments.
- No renderer or model execution is involved in this geometry diagnosis.

## Competing hypotheses

1. **Intentional toe-ground marker / toe roll.** `left_foot` and `right_foot` might represent a world-space planted toe while the ankle pivots above it. This predicts the constant marker is meaningful during contact only, and an explicit ankle-foot articulation or edge would define the pivot. It is ruled out if the same marker is frozen during swing with no orientation or changing edge geometry.
2. **Unintended foot-marker deformation.** The foot marker is intended as a joint attached to the ankle but stays at a fixed world height. This predicts ankle-foot distance changes during swing, with no declared segment linking them. It is ruled out if that distance remains constant or if the marker is intentionally excluded from the skeleton/rendered rig.
3. **Intentional articulated pelvis/torso motion.** Pelvis bob may be intended to be absorbed by changing hip/spine articulation. This predicts explicit joints/orientation or compensating positions that keep connected segment lengths stable. It is ruled out if lengths of declared pelvis-to-hip and pelvis-to-spine edges change with no modeled articulation.

## Diagnostic tests and outcomes

1. Inspect generator formulas and `BONE_EDGES` for a foot pivot/rotation representation. Confirmation for hypothesis 1 requires a modeled ankle-foot relationship and a contact/swing-specific articulation; static coordinates alone are insufficient.
2. Generate both variants and measure ankle-foot distances over contact and swing frames. A varying distance plus missing edge supports hypothesis 2.
3. Measure every declared torso/hip edge across the phrase. A changing length supports hypothesis 3's absence of explicit articulation and demonstrates validator coverage gap.
4. Add invariant segment checks and corruption tests only after the above measurements identify which structure the prototype actually encodes.

## Findings

- Before repair, the broad variant had ankle-foot distances from 0.10308 to 0.12778 m, while the foot marker stayed at z=0.055 m. The declared bone edges omitted ankle-foot. No foot orientation or toe-roll angle existed. Hypothesis 1 is not supported; hypothesis 2 is supported with high confidence.
- Before repair, pelvis-to-left-hip varied from 0.13601 to 0.15059 m and pelvis-to-spine from 0.324 to 0.360 m as pelvis z bobbed up to 0.036 m. No rotation or articulation channel accounted for the difference. Hypothesis 3 is not supported by the representation; the geometry was inconsistent with the declared stick-rig topology.
- After repair, ankle-foot is constant at 0.10308 m, with the foot marker moving with ankle height. Pelvis-attached hip and torso points translate with pelvis. The expanded validator measures all 19 declared segments; the broad sequence's maximum measured segment error is about 1.4e-16 m (floating-point roundoff), with a maximum adjacent-frame joint displacement of 0.07076 m.
- Seven focused tests pass, including altered foot-marker and torso-segment corruption rejection, and beat-boundary contact continuity.

## Scope limits

These checks establish static segment consistency and basic contact screening only. They do not establish realistic joint articulation, balance, biomechanics, style authenticity, or artistic quality.
