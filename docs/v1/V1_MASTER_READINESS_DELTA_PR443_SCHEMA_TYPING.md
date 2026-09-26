# V1 master readiness delta — PR-G26 seal metadata schema hardening

Status: append-only release-preparation evidence. No production, seal, canary,
merge, release or approval authority is implied.

## Exact baseline

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- prior ledger head before this write: `bb98d38ce3509a651af27020aa7c56f5794b35cc`
- PR-G26 repository-prep PR: #443
- predecessor #443 containment repair head: `4d70ddc7902237f4b7d1bd60ff1c82bd834e90a4`
- new #443 schema-hardening head: `d2c8bb907da0c51f0bd56c9f5cb0114816b93205`

## Finding

A supplemental synthetic challenge reported that, for a one-entry manifest, seal
metadata using JSON booleans or floats could satisfy cardinality comparisons
because Python equality makes values such as `true == 1` and `1.0 == 1` true.

This is a **schema strictness defect** in the recorded seal metadata comparison,
not a recurrence of the repaired symlink-containment escape and not evidence that
private production Seal v2 bytes were invalid.

## Repository repair

#443 now adds exact nonnegative integer validation for seal cardinality fields.
The verifier requires `type(value) is int`, which deliberately rejects booleans,
floats, strings and negative values. The check applies to:

- `authoritative_manifest.entry_count`;
- `authoritative_manifest.entries_verified`;
- `authoritative_manifest.entries_failed`;
- legacy `authoritative_evidence.sha256sums_verification.entries_verified`;
- legacy `authoritative_evidence.sha256sums_verification.entries_failed`.

A new focused test module, `tests/test_r4_seal_manifest_schema.py`, records the
negative controls for booleans, floats, strings and negatives plus a positive
control for exact integer metadata.

## Current status

At the time of this ledger write, GitHub Actions had not yet dispatched workflow
runs for exact head `d2c8bb907da0c51f0bd56c9f5cb0114816b93205`. Therefore:

- #443 schema-hardening patch: **IN_PROGRESS / awaiting exact-head CI**;
- previous #443 containment repair at `4d70ddc7...`: retained as green evidence
  for that older exact head only;
- full PR-G26: **BLOCKED / NOT VERIFIED**.

No old-head PASS transfers to `d2c8bb90...`. Terminal CI, artifact identity and
review disposition must be recorded in a later append-only delta.

## Boundaries unchanged

The symlink-containment repair remains intact but is now superseded by changed
bytes. The caller-selected package root must still be trusted and stable; the
source package must still be an immutable snapshot. This patch does not establish
closed-world membership, hard-link/mount closure, semantic candidate/gate/safety-
counter binding, provenance-DAG closure, private Seal v2 verification, human
review, approval, canary authorization or release authority.
