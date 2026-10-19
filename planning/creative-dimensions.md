# Creative variation needs an explicit dimension contract

The first live Gemma art-manager probe passed JobBoard schema validation, producing three pending jobs. Its distinct IDs described front/profile/three-quarter views. That does not establish three distinct silhouette designs. The trial had fixed pose but did not explicitly pin camera/viewpoint, so this is an under-specified creative contract and a validator coverage gap, not proven disobedience.

Next fixture should make axis and invariants first-class: fixed front camera, fixed pose, blue coat, no logo; vary coat silhouette across A-line, cocoon and straight. Store each design descriptor independently from job_id. Exact descriptors can be checked in the plan; actual generated image compliance and aesthetic value still need separate inspection.

Compare an explicit structured-dimension harness against the initial generic variation-ID harness. Record whether output is schema-valid, dimension-faithful and visually faithful separately. Preserve the original trial. Do not score uniqueness of labels as meaningful creative diversity.

Live follow-up: Gemma 4 26B A4B returned the required A-line/cocoon/straight structured descriptors while preserving front camera, fixed pose, blue coat and no-logo fields. Host validator passed; 369 prompt tokens, 160 completion tokens, 2.981 seconds, reported cost $0.00008023. Five focused tests passed. Evidence: evidence/creative-variants-live.json. This single prompt/schema revision is not a controlled statistical comparison, and plan compliance is not image fidelity or aesthetic quality.
