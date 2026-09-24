# RESIDUAL current status

_Observation: 2026-09-24 17:10 UTC. Fresh scope: accepted main, #443 PR-G26
schema-typing hardening, and #427 ledger reconciliation. Exact revisions below
are observed snapshots, not promises that moving branches remain unchanged._

This is a human-readable status record, not acceptance authority. Historical
PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt and
environment that produced it. Earlier detailed snapshots remain in git history,
including the 16:09 broad status at `2b106174...`, the 16:37 containment/CI
status at `1d38400e...`, and the later #444/#445 status immediately preceding
this observation. Those historical records are retained, not represented here as
fresh re-audits.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. This
observation does not merge any candidate into main. Release convergence remains
**BLOCKED**.

#443 is **OPEN / UNMERGED / UNACCEPTED** at observed head
**`d2c8bb907da0c51f0bd56c9f5cb0114816b93205`**. The previous repaired head
`4d70ddc7902237f4b7d1bd60ff1c82bd834e90a4` remains retained as the green
symlink-containment repair: 26/26 focused local tests passed and all seven named
technical workflows passed on that exact older head. The new `d2c8bb90...` head
adds strict seal metadata integer typing and a new focused schema test module.

At the time of this observation, GitHub Actions had not yet dispatched workflow
runs for `d2c8bb90...`; therefore the new #443 head is **IN_PROGRESS / awaiting
exact-head CI**. Old-head PASS results do not transfer.

Draft #427 is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at observed head
**`676cd6af84934762d130ed3f0998bdd2cde3cdda`**. It now contains the append-only
`docs/v1/V1_MASTER_READINESS_DELTA_PR443_SCHEMA_TYPING.md`, recording the schema-
typing finding, repair scope, and pending-CI status. Older ledger identities are
historical snapshots only.

No corrected seal, private Seal v2 verification, independent human acceptance,
canary authorization, physical F6 evidence, RC, deployment, release or production
acceptance follows from these changes.

## PR-G26 — current #443 state

The symlink-containment defect remains repaired in the prior exact head. That
repair used anchored descriptor-relative no-follow traversal, regular-file checks
on opened descriptors, canonical POSIX paths, same-read manifest digest binding,
and fail-closed unsupported-platform behavior. Its limitations remain explicit:
trusted/stable caller-selected package root, immutable input snapshot, no hard-
link/mount isolation proof, no arbitrary concurrent-content-mutation proof, no
closed-world membership, no semantic candidate/gate/safety-counter binding, and
no provenance-DAG closure.

The new #443 schema-typing hardening addresses a separate strictness issue: JSON
booleans and floats could satisfy equality comparisons for one-entry seal counts
because Python treats `true == 1` and `1.0 == 1`. The verifier now requires exact
nonnegative JSON integer counters using `type(value) is int`, excluding bools,
floats, strings and negatives.

The check applies to:

- `authoritative_manifest.entry_count`;
- `authoritative_manifest.entries_verified`;
- `authoritative_manifest.entries_failed`;
- legacy `authoritative_evidence.sha256sums_verification.entries_verified`;
- legacy `authoritative_evidence.sha256sums_verification.entries_failed`.

New focused coverage is in `tests/test_r4_seal_manifest_schema.py`, including
negative controls for booleans, floats, strings and negative values plus a
positive exact-integer control.

## Current status and required next evidence

- #443 `d2c8bb90...`: **IN_PROGRESS / awaiting exact-head CI**.
- #427 `676cd6af...`: **ledger updated / awaiting its own exact-head evidence if accepted**.
- #364 current document: **documentation-only observation**, not review or acceptance.
- PR-Agent and maintainer approval remain separate; this update does not create a
  formal human review or attestation.

Full **PR-G26 remains BLOCKED / NOT VERIFIED** pending exact-head CI for the new
schema-hardening bytes, genuine independent human review, and separately retained
private direct-source semantic/provenance verification of the authoritative
runtime package and final Seal v2.

## Other retained gates

#444 PR-G28 lock-contract tooling and #445 claims-contract proposal remain in
their previously recorded states. They are not advanced by this #443 schema
hardening. V1-CLAIMS-001 owner/operations approval, deployment/trust profile,
AUD-1/#353 closure, physical F6-A/F6-B, Mason/LEGION re-audit, canary, exact-RC
recovery/incident/elapsed-soak evidence and final human release authorization
remain outstanding.

No frozen artifact, seal, authoritative runtime package, live service, credential,
canary, production system, AUD-1 branch or research branch is modified. No merge,
auto-merge, approval, attestation, physical execution, deployment, drill, soak,
tag or release is requested or claimed.
