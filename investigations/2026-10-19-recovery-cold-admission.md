# Cold model reply missed admission

The first live E2B lifecycle trial never began playback. Competing explanations were malformed intent, a host recovery regression, and a legitimate reply arriving after the five-second deadline. The raw response contains the exact requested sway/accents; delivery explicitly records rejected_deadline. Provider wall time was 5,866ms and request-to-delivery 6,156ms. Native timing attributes 5,265.7ms to loading, 171.5ms to prefill and 371.9ms to decode. No recovery had begun.

The discriminating followup reused the same instruction and unchanged runtime on a fresh finite viewer while the model was warm. Both requests were admitted and all 22 lifecycle checks passed. This supports startup latency as the observed failure mechanism; it does not justify deleting the cold failure or widening the deadline. No implementation correction was made. All receipts and the exact hash-matched first runner are retained.
