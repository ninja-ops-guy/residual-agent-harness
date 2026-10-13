# V1 master readiness delta — PR-G26 integration successor

This is an append-only evidence refinement to the review-only v1 master ledger.
It does not authorize a canary, merge, deployment, physical test, release, tag,
attestation, production mutation, or modification of any frozen artifact.

## Baseline re-read before write

- accepted `main`: `d796f36b75e730a0bab71bdba564206174393719`
- prior master-ledger head: `485e9d797dbef0f9120f014f06fcd3d6fb905fda`
- frozen R4.1 candidate remains reference-only:
  `8701367db6d3202f24b3eb9f4696b0cadf657985`
- frozen tree remains reference-only:
  `79bfe6ed1743907065ed44aeb9c460c47527e0c6`

## PRE-CANARY — V1-PC-001 / PR-G26 evidence-integrity gate

### Requirement / acceptance criterion

Before canary authorization, direct-source seal verification must recompute every
applicable authoritative claim from its named source rather than trusting a
derived summary. At minimum the selected independent/frozen verifier must:

- parse and hash the authoritative manifest directly;
- derive cardinality without caller-supplied expected counts;
- reject malformed, duplicate, unsafe, missing, or digest-mismatched entries;
- bind the candidate HEAD/tree, complete gate/status set, safety counters,
  unresolved-gate set and final disposition to authoritative source records;
- enforce an explicit package-closure policy where closed-world semantics are
  claimed;
- reject derived-to-derived provenance as evidence authority;
- fail closed on missing/unavailable/private evidence.

### Sources

- production audit #423 exact head
  `324a8421205c664cb4cfbfda9582a6e79d43ee64` — PR-G26.
- cardinality tooling #415 exact head
  `3da0d8ec45adf8934b88906462706617aa22831f`.
- adversarial characterization #422 exact head
  `31dc9c1bf88ee69f417f53c0f4ff5558fc48f645`.
- new current-main integration successor #443 exact head
  `d4af45bd07abf96d60c834c060395e5619731583`.

### Classification

Observed historical evidence-authority defect + verified proposed repository
tooling + **missing private direct-source semantic verification evidence**.

### Dependency / owner / implementation

- dependency: no production/canary gate may treat derived seal metadata as
  authority;
- repository preparation owner: Release Convergence lane;
- private-source execution and independent review: operator / independent
  evidence reviewer;
- implementation successor: #443.

### Test / evidence status on #443 exact head

At the time of this delta:

- Clean install qualification `36021595076` — PASS;
- Factory ownership gate `36021594991` — PASS;
- Control Plane `36021594837` — PASS;
- Measured evaluation acceptance binding `36021595110` — PASS;
- Qualification-v1, controller/provider contracts and Command Station checks —
  still running; no result inherited from #415/#422;
- Maintainer approval gate `36021594770` — expected FAIL because no human
  exact-head attestation exists;
- PR-Agent advisory `36021594692` — unavailable: secret preflight passed,
  model execution failed with `credit_balance_exhausted`, and no substantive
  advisory was published.

### Verification status

- #415/#422 source tooling: historical/review evidence only.
- #443 repository integration successor: **IN_PROGRESS** pending its remaining
  exact-head technical CI.
- cardinality/direct-manifest sub-requirement: reviewable tooling exists.
- **PR-G26 parent gate: BLOCKED / NOT VERIFIED.**

The earlier ledger shorthand that displayed PR-G26 as
`READY_FOR_REVIEW` must be read as applying only to the repository-side
cardinality/verifier tooling. It must not be interpreted as complete
direct-source semantic seal verification.

### Required human/operator action

After #443 receives normal review and any accepted integration is selected,
execute the independently reviewed/frozen verifier read-only against the private
authoritative `runtime-20260924T025450Z` package and final Seal v2. Retain only
a sanitized result binding verifier digest, authoritative manifest digest,
candidate identity and Seal v2 digest. GitHub-only access cannot perform this
step, and absence of the private evidence remains `BLOCKED`, never `PASS`.

## PRE-CANARY — V1-PC-002 / V1-PC-003 / V1-PC-004

No status promotion occurred.

#426 exact head `494dac7c0702a285c33ceddd3f0237f63ceea425`
still reports, from disposable synthetic frozen-candidate probes:

- malformed/cross-project/cross-operation receipts becoming local `ACKED`;
- recovery POST after stored-payload digest mismatch;
- two simultaneous recoverers each issuing POST.

This run did **not** independently reproduce those observations. The GitHub
repository API could not resolve the frozen candidate SHA, and the obvious
Shared-Comms continuity/outbox implementation is currently owned by active
draft #404 rather than accepted main. Creating a competing repair would violate
single-writer/branch ownership and would not satisfy the requested reproduction
standard.

Statuses remain:

- V1-PC-002 — `BLOCKED`, explicit receipt-threat-model disposition required;
- V1-PC-003 — `BLOCKED`, explicit local-state-tamper/digest disposition required;
- V1-PC-004 — `BLOCKED`, explicit single-owner vs concurrent-recovery topology
  disposition required.

No finding was relabeled optional to clear a gate.

## PRE-PRODUCTION — AUD-1 ownership boundary

Read-only tracking only; no AUD-1 branch was edited.

- #438 exact head
  `e815f33484352f100e11b8d075bb954a815244cc` is the current software-repaired
  C1-C6 successor and remains human-review/owner-selection HOLD.
- #439 exact head
  `2edee868c30c0a349adb45bff8fbded102fb783c` is preparation tooling only and
  does not select/retarget the frozen #403 helper.
- issue #353 physical F6-A/F6-B, independent Mason/LEGION re-audit, exact
  selected-head qualification, genuine owner attestation, guarded integration
  and resulting-main requalification remain outstanding.

The Closure task remains the single writer for this lane.

## Readiness movement

One P0 evidence-integrity blocker now has a current-main integration successor
(#443) under exact-head CI. This is repository preparation progress, not
production acceptance and not canary authorization. The full PR-G26 direct-source
verification, V1-PC-002..004 scope decisions, deployment-profile authority,
AUD-1 physical/independent closure, recovery/rollback/drill evidence, soak and
human release authorization remain open.
