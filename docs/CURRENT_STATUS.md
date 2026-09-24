# RESIDUAL current status

_Observation: 2026-09-24 16:33 UTC. Fresh scope: accepted main, #443 containment
repair and checks, and #427 ledger reconciliation. Exact revisions below are
observed snapshots, not promises that moving branches remain unchanged._

This is a human-readable status record, not acceptance authority. Historical
PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt and
environment that produced it. The full preceding 16:09 snapshot, including its
AUD-1 and other tooling details, is retained in
[git history at 2b106174](https://github.com/ninja-ops-guy/residual-agent-harness/blob/2b106174e5d084a0bc0e1116eea44ad23ff8d5da/docs/CURRENT_STATUS.md).
Those historical observations are not represented as fresh re-audits here.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**,
the merge of #304. This observation does not merge any candidate into main.
Release convergence remains **BLOCKED**.

The actual filesystem-containment defect in #443 has been reproduced and
repaired on its own branch. #443 is **OPEN / UNMERGED / UNACCEPTED** at
**`4d70ddc7902237f4b7d1bd60ff1c82bd834e90a4`**, tree
`59bb37151bdda4434531557f33d38cef8cca178a`. Local focused tests pass 26/26;
fresh hosted qualification is recorded separately below and is not inherited
from the pre-repair head.

Draft #427 is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at observed head
**`07f7686643ccc9f2206fa146a78b01dc4568dd3b`**. The newly appended
`docs/v1/V1_MASTER_READINESS_DELTA_PR443_CONTAINMENT.md` preserves the finding,
repair identity, local evidence and pending hosted results. Its claims-contract
and PR-G28 deltas remain intact. The older `485e9d79...`, `ace6968d...`,
`e543c066...` and `4e648c6d...` references are historical snapshots, not this
observation's ledger head.

No corrected seal, private Seal v2 verification, independent human acceptance,
canary authorization, physical F6 evidence, RC, deployment, release or production
acceptance follows from these changes.

## PR-G26 — manifest/cardinality and symlink containment

At retained #443 head `d4af45bd07abf96d60c834c060395e5619731583`, the
verifier performed lexical path checks but followed symlinks when checking and
opening files. A direct file symlink and a symlinked parent directory both
returned PASS for matching disposable external bytes. Existing 11 tests passed
despite that defect. Therefore the earlier phrase "rejects unsafe entries" did
not establish filesystem containment. This was an **implementation defect** as
well as a missing documentation caveat; original code and evidence remain in
history.

The new #443 verifier walks referenced directory components relative to an
anchored directory descriptor using `O_DIRECTORY | O_NOFOLLOW`, opens the leaf
without following symlinks, checks that the opened object is a regular file,
and hashes that descriptor. Internal and external symlinks, a symlinked
manifest, directory/FIFO targets, and noncanonical POSIX aliases are rejected.
The reported manifest digest binds the same bytes that were parsed and counted.
Unsupported secure-open platforms fail closed.

Published verifier blob: `d29f245c9d25668df23f95c1bce7874da7080321`.
Verifier SHA-256:
`fe36e3a00e2b3d6233e0029ddf60aec4b5963e9df082a59d7c88e11be4a9f00e`.
Published adversarial-test blob: `00cd13a62aefbd14e8d2aeabdb0e8a2bb4b4c0b5`.
These exact source/test bytes passed **26 focused tests, zero failures/errors/
skips**, locally on Linux/Python 3.13.5. The 15 new containment tests include
leaf/parent swaps immediately before open, use of an already-open parent across
pathname replacement, same-read manifest digest binding and descriptor cleanup.

**Remaining limitations:** the caller-selected package root must be trusted and
stable and the input must be an immutable snapshot. This is not a hard-link or
mount-isolation proof, a proof against arbitrary concurrent content mutation,
closed-world membership, semantic candidate/gate/safety-counter binding, or
provenance-DAG closure. Native Windows verification is not qualified here.

Full **PR-G26 remains BLOCKED / NOT VERIFIED** pending independent review/freeze
of the exact verifier and independently retained read-only semantic/provenance
verification of the private authoritative runtime package and final Seal v2.
See #443's `docs/v1/V1_PR_G26_DIRECT_SOURCE_HANDOFF.md` for the acceptance boundary.

### Fresh #443 hosted checks on 4d70ddc7

| Workflow | Run | Observed result |
| --- | --- | --- |
| Clean install | 36027756115 | PASS |
| Factory ownership | 36027756068 | PASS |
| Control Plane | 36027755898 | PASS |
| Measured-evaluation binding | 36027755923 | PASS |
| Qualification-v1 | 36027756278 | IN_PROGRESS |
| Controller/provider | 36027755996 | IN_PROGRESS; Python 3.11/3.13 jobs passed, 3.12 still running |
| Command Station | 36027756038 | IN_PROGRESS |
| PR-Agent advisory | 36027755998 | FAIL at advisory review after secret preflight; publication verification skipped |
| Maintainer approval | 36027756119 | Policy self-tests PASS; explicit exact-head approval requirement FAIL |

No old-head PASS is transferred to this repair. The unavailable advisory is not
product acceptance or independent review. No advisory retry, human approval or
attestation was issued by the remediation lane. Later terminal results require
a new timestamped observation.

## R4.1 evidence authority and canary boundary

The prior external R4.1 qualification remains bounded to its authoritative
candidate, source evidence, hashes and gates. The propagated `44/44` seal wording
is invalid derived metadata. #415 records that the count was manually embedded
after a hash check, while the authoritative manifest contained 50 valid entries.
The defect does not by itself rewrite candidate identity or historical runtime
gate results, but the erroneous seal cannot serve as authorization evidence.

A corrected seal and independent private-source acceptance are **not established
by this observation**. Canary remains **NOT AUTHORIZED / NOT EXECUTED** in the
retained ledger. No sealed artifact or private runtime source is modified here.

## Claims contract, deployment profile and dependency matrix

The retained #427 claims delta makes **V1-CLAIMS-001 / #445** the controlling
owner/operations decision: approve v1 promises and enforceable exclusions before
closing applicability decisions. #445 is a proposal, not an approval receipt.
Deployment/trust profile, canary threat model, release dependency matrix and
acceptance/soak procedures derive from that approved contract.

The #444 PR-G28 tooling snapshot is
`1403429dbdcb3abf04bcb1fb75fd1a2bad93cfbc`. Its recorded technical checks are
review-ready, but a validator is not a complete authoritative transitive lock.
Approved release matrix, separately authorized dependency resolution, hashed
artifacts, offline/reproducible build and exact-RC binding remain outstanding.
PR-G28 remains **BLOCKED / NOT VERIFIED**.

#426 / V1-PC-002..004 findings still require explicit scope/threat-model
reconciliation. An exclusion must be approved and enforced; documentation alone
does not exclude a reachable capability. None of these parent gates advances
through the #443 containment patch.

## AUD-1 security convergence — retained, not re-audited here

Issue #353 remains the separate security-closure owner. The preceding snapshot
records it OPEN with no milestone and physical F6-A/F6-B **UNKNOWN / not
established**. This observation adds no physical or independent audit evidence.
Original #399/#403 candidates and evidence remain frozen.

The retained #438 head is `e815f33484352f100e11b8d075bb954a815244cc`, stacked
on #433 `9b4f32ce71ba2f4520dc1d7c2d8826fa329bdf60`. Its bounded-drain repair,
old failing test-only head, exact-head CI/artifact evidence and approval gap are
preserved in the pinned preceding status record. They are not requalified by
this documentation change.

Required order remains: genuine independent human review; deliberate successor
selection and helper reconciliation; separately retained F6-A/F6-B real-host
evidence; Mason/LEGION read-only re-audit; exact-head qualification and owner
attestation; guarded integration and authoritative resulting-main qualification;
then exact-RC recovery and elapsed-soak evidence. No fixture replaces physical
F6 execution.

## Other release-preparation lanes — historical evidence retained

| Lane | Retained scope and unresolved acceptance |
| --- | --- |
| #428 | Frozen R4.1 canary provenance is separate from the eventual post-convergence RC. |
| #429 | Metadata consistency tooling; final 1.0.0 normalization belongs to RC/release. |
| #430 / #436 | ENV-G01 capability tooling and retained broad-suite environment triage; neither makes unrelated failures PASS or proves integrated-main readiness. |
| #432 | Deployment-profile validator; topology, trust, SLO/RPO/RTO, backup/HA and soak policy remain owner/operations decisions. |
| #434 / PR-G30 | Incident-response contract; independently retained execution of the five authorized drills remains required. |
| #435 / PR-G07 / PR-G21 | Recovery validator is VALIDATION_ONLY; production-shaped backup/restore/rollback exercises and exact-RC approval remain required. |
| #437 / #440 / PR-G27 | Immutable-Action audit/remediation; independent pin review, SBOM/provenance/tamper evidence, guarded merge and resulting-main requalification remain incomplete. |
| #441 / #442 | Open Core export/governance candidates remain separate from legal/ownership clearance, license grant on accepted main, funding acceptance and release authority. |

The earlier detailed exact heads, run IDs, artifact digests and failure
classifications for these lanes are preserved in the preceding snapshot and
append-only #427 deltas. They were not all re-fetched in this containment update;
no fresh acceptance claim is made for them.

## Qualification and documentation discipline

A PASS is specific to the tested revision and environment. Software tests do
not establish physical F6 behavior, private seal validity, canary success,
production recovery, incident readiness, elapsed 24h/72h/30d soak, blanket
multi-host M4 qualification, or production acceptance. Those remain separate
applicable gates and explicit human decisions.

The accepted Factory/M4 ownership baseline remains whatever main records.
`implementation-status.yaml` records implementation presence, not release
qualification. This documentation update does not alter Factory/M4 code/tests,
ownership baselines, qualification anchors, evidence schemas, provider authority,
security implementation, licensing authority or acceptance authority.

This observation changes only `docs/CURRENT_STATUS.md` on #364. Earlier README
and HARNESS edits on that branch are not changed. No main write, merge,
auto-merge, approval, attestation, canary, live-service action, credential change,
physical test, seal operation, deployment, tag or release is authorized. Exact-head
human review remains required before accepting this documentation PR.
