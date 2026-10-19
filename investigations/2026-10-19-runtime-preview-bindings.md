# Runtime preview schema binding

Expected: render the six-call runtime record without changing provider evidence. Observed during pre-render review: the draft renderer imports the original motif cases and expects per-call compiled/intent/motion_receipt fields. Direct inspection of the runtime record shows those fields absent. No renderer was executed yet. Prior motif renderer used the original comparison record; this is a new renderer for a new record.

## Diagnostic plan

1. Wrong input file: inspect EVIDENCE_IN and report scope/call count. Confirm if it points at the earlier 84-call comparison; rule out if it names the six-call runtime record.
2. Incomplete run omitted fields: inspect complete flag and runtime probe writer; confirm if the writer normally emits these keys but execution did not finish; rule out if the writer intentionally records raw responses/delivery only.
3. Renderer copied old assumptions: inspect imports, per-call accesses and actual report keys; confirm if the renderer uses old fixture/receipt shapes absent from the completed runtime writer.

Use saved raw records and source code, not retrospective notes. Renderer author will fix verified bindings; frozen model evidence remains unchanged. Existing autonomous experiment authorization covers this reversible correction.

## Findings

The input path correctly names the completed six-call runtime record, ruling out the wrong-file hypothesis. The runtime writer deliberately saves raw responses and delivery outcomes without the older comparison's compiled/intent/motion_receipt fields; complete=true and the saved writer distinguish this from an interrupted run. The draft renderer had copied the earlier comparison schema and fixture import. The author corrected those bindings, recompiles the raw content and verifies initial/replacement admitted hashes; the stale response is compiled for provenance but never treated as admitted. Offline validation passed for two runs, six calls and 141 samples each. No model evidence changed or extra provider calls were made.
