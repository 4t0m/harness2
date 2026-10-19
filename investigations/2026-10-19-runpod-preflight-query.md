# RunPod read-only preflight query

The minimal current pods/GPU-type query succeeded, with zero pods. A combined single-5090 quote plus User-field introspection returned HTTP400. No resource mutation was requested. Need distinguish query validation from access or availability.

Plan: (1) Capture bounded GraphQL error messages for the exact request; validation location/type errors support field/schema mismatch, authentication errors support key permissions. (2) Remove introspection and repeat only the documented quote query; success isolates introspection/combined operation restrictions, same error favors quote schema mismatch. (3) Use published primary API schema for billing fields; do not guess an account balance or infer unavailable stock from HTTP400. Preserve request shapes and sanitized diagnostics; never keys or headers.

The exact error explicitly rejects GraphQL introspection (__type/__schema) in production. The quote-only query is the supported operation; introspection failure is not an authentication, capacity, or billing failure. Use published schema documentation for any billing field rather than probing introspection again.
