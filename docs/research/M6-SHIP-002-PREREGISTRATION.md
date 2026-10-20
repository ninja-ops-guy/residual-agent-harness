# M6-SHIP-002 Preregistration — Actionable Repair Evidence

M6-SHIP-001 failed closed because the candidate returned bytes from canonical_json instead of str. The semantic check used a bare assertion and retained only an opaque line-number failure. Attempts 2–5 reproduced the exact same failed patch.

M6-SHIP-002 keeps unchanged:
- roadmap instruction;
- writable scope;
- source repository import;
- model and runtime;
- acceptance semantics;
- attempt/token/wall-clock bounds;
- review, receipt, integration, and promotion boundaries.

The only experimental change is **diagnostic quality**. Every semantic failure in the acceptance command now emits a named expected/actual message suitable for repair.

Primary hypothesis:
> precise deterministic failure evidence allows the bounded repair loop to correct an otherwise stagnant candidate without weakening the acceptance contract.

Success remains: 2/2 checks, review approval, integration receipt, release export, generated source retained.

If an unchanged failed candidate repeats despite actionable evidence, the stagnation detector proposed in issue #235 becomes a higher-priority harness requirement.
