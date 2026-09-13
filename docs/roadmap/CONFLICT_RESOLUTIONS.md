# Binding resolutions applied to the foundation

These resolutions come from the user's September 13, 2026 handoff. The new code archive did not contain a `CONFLICT_RESOLUTIONS.md`; this file records the supplied decisions explicitly.

1. **Freeze at construction.** `LoopController(..., extensions=registry)` freezes the registry in its constructor. It remains frozen across runs. A different module set requires a new registry. Each registry admits one active run; different projects use different registries.
2. **Propagate downward with data flow.** A task records its prerequisite receipts. Changed verifier, evidence, or prerequisite identity invalidates dependent bindings; arrival order does not.
3. **UNKNOWN is non-accepting.** Missing evidence remains distinguishable from demonstrated failure. Unknown checks block success and skip subsequent judge checks.
4. **Retain all seven normative receipt fields.** The latest status says “six fields,” but WORLD_CLASS_SPECS and the agreed foundation name seven: task ID, cache key, value hash, verifier name, verifier revision, verdict, and parent receipts. All seven are retained. Envelope schema/algorithm/hash metadata is additional.

These decisions supersede contrary timing or parent/child terminology in the preserved source drafts. Historical formats are not relabeled as new receipts.
