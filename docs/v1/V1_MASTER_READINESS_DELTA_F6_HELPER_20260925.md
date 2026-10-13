# V1 master readiness delta — F6 helper successor and current release blockers

Status: append-only coordination evidence. This file does not authorize merge, canary, physical execution, deployment, soak, tag, release, approval, or attestation.

## Exact baseline

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- master-ledger parent immediately before this write: `8df60000b8b148af125114acc6eb25be98d715c5`
- frozen R4.1 candidate remains reference-only: `8701367db6d3202f24b3eb9f4696b0cadf657985`
- issue #353 remains the AUD-1 gate-order authority.
- Docs Watch/status PR #454 is a separate documentation lane and is not release authority.

## PRE-PRODUCTION — AUD-1 / CV-06 / F6

### V1-PP-002 — selected AUD-1 candidate

Source: #448 exact head `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`, tree `d8112fe34954ae6ed46544d81eeb951f94f9d95c`, base #438 `e815f33484352f100e11b8d075bb954a815244cc`.

Classification: observed candidate state + owner governance disposition.

Acceptance criterion for this row: one immutable AUD-1 candidate is selected for downstream qualification without claiming production acceptance.

Evidence:
- Qualification-v1 `36080373837` PASS.
- Command Station `36080373820` PASS, including native Windows ownership qualification.
- controller/provider, clean install, Factory ownership, Control Plane, measured-evaluation binding and Pages also PASS on that exact head.
- owner exact-head security/maintainer records are retained on #448.
- submitted GitHub review objects remain zero; the solo-maintainer compensating process is not independent third-party human review.

Status: **VERIFIED for exact candidate selection / NOT production acceptance**.

Dependencies: helper successor qualification, physical F6-A/F6-B, post-F6 read-only re-audit, exact-head/reintegrated qualification.

Owner: existing RESIDUAL v1 Closure/AUD-1 single-writer lane.

Required human action: none for candidate identity itself unless bytes change. Any source change invalidates the current exact-head evidence.

### V1-PP-003 — F6 helper successor

Source: #453 exact head `e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`, tree `edf2049529e6b80f503fa83eeca8936025e0ec9e`, parent #452 `6a4518ebf37ec6f089ec28093d65b0caabc6c619`.

Classification: verified unmerged repository tooling.

Acceptance criterion: helper bytes are bound to the selected #448 candidate, contain no stale executable/check-out target, pass fresh exact-head technical qualification, and have explicit exact-head maintainer disposition before physical use.

Evidence:
- #453 changes only `tools/aud1/README.md`: one insertion / one deletion correcting the example from exact-399 checkout to exact-448 checkout. Executable helper semantics remain those qualified through #452.
- Qualification-v1 `36085661604` PASS.
- controller/provider `36085661501` PASS.
- Command Station `36085661508` PASS.
- clean install `36085661574` PASS.
- Factory ownership `36085661581` PASS.
- Control Plane `36085661546` PASS.
- measured-evaluation binding `36085661671` PASS.
- PR-Agent `36085661475` FAIL; no product failure is inferred from that advisory result.
- combined exact-head status contains `maintainer-approval: success` from run `36087876973`, description `exact-head maintainer approval: ninja-ops-guy`.
- submitted GitHub review objects: zero.

Status: **VERIFIED / qualified helper successor, OPEN / DRAFT / UNMERGED**.

Dependencies: selected #448 candidate above.

Owner: existing RESIDUAL v1 Closure/AUD-1 single-writer lane.

Required human action: preserve #453 bytes for the authorized physical run. Any helper change requires a separately qualified successor.

### V1-PP-004A / V1-PP-004B — physical F6-A and F6-B

Source authorization: #453 owner comment binding selected candidate `943c77a...` and helper `e8e1a67...`.

Classification: missing physical evidence.

Acceptance criteria:
- F6-A: real remote runner owns a disposable task; transport interruption/recovery occurs inside the real retry/authority window; continuity is valid and no duplicate/stale authority is accepted.
- F6-B: interruption extends beyond the real authority window; old worker/lease is dead after restoration; stale result is rejected after reassignment/recovery.
- cases are separately retained evidence bundles using the exact authorized candidate/helper bytes and real configured timing; no manufactured Station state or shortened authority interval.

Status: **BLOCKED / NOT EXECUTED**.

Dependencies: exact clean candidate launch witness and digest; disposable remotely owned task; identified authenticated transport control; remote runner probe/log context; access to authorized physical topology.

Owner: physical operator / v1 Closure lane.

Required human action: perform the separately authorized real-host cases when prerequisites are present, preserving private logs/evidence outside public PRs and publishing only sanitized hashes/status.

## PRE-CANARY — evidence authority / Shared Comms

### V1-PC-001 / PR-G26

Source: #447 exact head `ad524c461aa60426695f226f541e172c557b8e98`, stacked on #443.

Classification: verified unmerged bounded verifier tooling + missing private evidence.

Status: #447 bounded JSON-boundary repair remains **READY_FOR_REVIEW**; full PR-G26 remains **BLOCKED / NOT VERIFIED**.

Acceptance still requires the retained direct-source/private verification, exact verifier selection, semantic/package closure and provenance policy. No private Seal/runtime evidence is claimed by this delta.

### V1-PC-002..004 / #426

Source: #426 exact head `494dac7c0702a285c33ceddd3f0237f63ceea425`.

Classification: reported observed findings from retained disposable probes; not independently reproduced by this delta.

Open findings remain explicit:
- malformed/wrong-project/wrong-operation receipt may become ACKED;
- stored payload digest is not verified on recovery before POST;
- simultaneous recoverers may issue two POSTs.

Status: **BLOCKED pending final Shared Comms inclusion/exclusion and bounded threat-model disposition**. If included, applicable semantic binding, recovery-digest and ownership requirements remain pre-release gates. If excluded, exclusion must be enforceable, not documentation-only.

## PRE-PRODUCTION — supply chain / reproducibility / claims

### PR-G27

Source: #440 exact head `72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`.

Classification: verified top-level pin tooling plus unresolved transitive/audit-coverage findings.

Status: **BLOCKED / NOT VERIFIED** at parent-gate level. Retain the structural YAML-auditor gap and mutable transitive-input findings; do not treat top-level 40-hex PASS as complete dependency closure.

### PR-G28

Source: #444 exact head `78c34d3d7fde7b5edf8488a0842acb96270cfb95`.

Classification: verified unmerged lock-contract tooling + missing authoritative build evidence.

Status: tooling **READY_FOR_REVIEW**; parent PR-G28 **BLOCKED / NOT VERIFIED** pending approved release matrix, authoritative complete transitive lock generation, hash-enforced network-disabled install/build, reproducibility comparison and exact-RC binding.

### V1-CLAIMS-001

Source: #445 exact head `9eba077817720021174671ba1652b59fb801b670`.

Classification: scope decision.

Status: **BLOCKED** pending owner/operations approval of remote transport, Shared Comms include/exclude, full OS/architecture/Python/artifact/extras matrix, availability/RPO/RTO/backup policy and soak contract. The bounded AUD-1 Linux/x86-64 ownership scope does not silently approve the complete release matrix.

## CANARY / POST-CANARY / RELEASE

- Historical R4.1 17/17 READY_FOR_CANARY: retained historical exact-scope qualification only.
- canary authorization/execution: **BLOCKED / NOT EXECUTED**.
- post-canary verifier execution: **NOT_STARTED**.
- converged exact RC: **NOT_STARTED**.
- resulting-main and exact-RC recovery/incident/provenance qualification: **NOT_STARTED**.
- elapsed soak: **NOT_STARTED**.
- final release authorization/tag/archive: **NOT_STARTED**.

## R5 / POST-V1 / RESEARCH

No R5/research lane is promoted onto the v1 critical path by this delta. #450/#451 and earlier #410/#411/#419/#420/#421/#424 work remain research/post-v1 unless a separately verified release finding explicitly promotes an item.

## Current dependency order

1. Preserve exact #448/#453 candidate/helper bytes.
2. Satisfy real-host prerequisites and execute authorized F6-A and F6-B as separate retained cases.
3. Perform standing Mason/LEGION read-only post-F6 re-audit of F1/F2/F3/F4/F6.
4. Complete required unchanged-head/final AUD-1 qualification and owner disposition, then guarded integration and resulting-main qualification.
5. Resolve #445 release profile and Shared Comms scope; apply that disposition to #426.
6. Complete PR-G26 private semantic/provenance verification, PR-G27 transitive supply-chain closure and PR-G28 authoritative lock/offline reproducibility evidence.
7. Only after applicable gates converge: freeze exact RC, perform recovery/incident/provenance qualification, run separately authorized elapsed soak, then obtain final human release authorization.

No frozen candidate, Seal v2, authoritative runtime, failed historical evidence, research experiment, live host/service, credential, tunnel, production state or protected ownership pin was modified by this ledger update.
