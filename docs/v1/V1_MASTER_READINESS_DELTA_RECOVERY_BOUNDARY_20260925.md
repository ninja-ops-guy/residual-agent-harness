# V1 master delta — recovery evidence validator boundary

Status: review-only, append-only release preparation. Observation date: 2026-09-25 ET.
This record does not grant operational or release authority.

## Exact identities and scope

- Accepted main: `d796f36b75e730a0bab71bdba564206174393719`.
- Master parent immediately before write: `0c1ce2918af6e2eef3c22e9099a50edeacb8118d`.
- Original recovery proposal #435: `378207e511550532dbba60e8d4ae489666aa6c09`, unchanged.
- New focused successor #461: `d4027aa261bc3a4e2fa029479498850e7a9a5564`, directly based on accepted main, DRAFT / UNMERGED.
- Repair branch: `repair/v1-recovery-evidence-json-boundary`.
- #461 carries the #435 validator plus its unchanged ten tests and a bounded parser/numeric correction; its overlap with #435 must be reconciled during review, not integrated twice blindly.

Ownership: v1 repository-release-preparation lane. The live recent-PR search and
#435 source/comments were inspected before work; no competing repair was found
in those results. AUD-1/F6, Shared Comms runtime, archive extraction and Docs
Watch branches were not edited. #460 was discovered as research-only material;
it does not become a v1 requirement.

## PRE-PRODUCTION — PR-G07 / PR-G21 tooling findings

All four rows are observed defects in the unmerged #435 validator, not observed
production recovery failures. Their implementation status is IN_PROGRESS:
local exact-source regression evidence exists, but fresh hosted qualification
and human review must complete before this successor is accepted.

| Stable ID | Acceptance criterion | Classification | Dependencies | Owner | Implementation | Test / evidence | Status | Required human action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REC-JSON-01 | Known API RPO/RTO metrics reject non-finite values; raw JSON rejects NaN/Infinity and overflowing exponents at any depth, without PASS. | observed finding | #435 contract | v1 release-preparation | #461 exact head above | API and CLI non-finite regressions; original failures retained | IN_PROGRESS | Review exact successor and fresh CI |
| REC-JSON-02 | Raw JSON rejects duplicate decoded member names at every object depth, including escaped/equal duplicates; last-value replacement cannot hide an invalid claim. | observed finding | #435 contract | v1 release-preparation | #461 | Root, approval, metric and nested duplicate controls; same tests fail on predecessor | IN_PROGRESS | Review parser boundary and preserve original negative controls |
| REC-NUM-03 | Integer comparison preserves a one-unit objective breach beyond binary-float exact range; large finite integer breaches return FAIL rather than an overflow exception. | observed finding | #435 contract | v1 release-preparation | #461 | Direct API and CLI `2**53 + 1` controls, large-integer failure control | IN_PROGRESS | Review precision/finite-float scope; do not infer arbitrary decimal precision |
| REC-INPUT-04 | Invalid UTF-8 CLI input and non-object direct API input produce typed failure, never PASS or an unstructured traceback. | observed finding | #435 contract | v1 release-preparation | #461 | Encoding/root negative controls, ordinary valid-input controls retained | IN_PROGRESS | Review structured error behavior |
| PR-G07 / PR-G21 acceptance | Approved profile and exact RC, separately authorized production-shaped backup/restore/rollback exercises, independently retained evidence and genuine human qualification. | missing evidence / scope decision | #445/#432 profile, selected RC, accepted validator | owner/operations/qualification lead | #435 contract + proposed #461 correction | No operational exercise performed in this pass | BLOCKED | Approve profile and subsequent exercise/evidence acceptance separately |

Requirement source:
https://github.com/ninja-ops-guy/residual-agent-harness/blob/378207e511550532dbba60e8d4ae489666aa6c09/docs/v1/V1_RECOVERY_QUALIFICATION.md

Implementation and detailed provenance:
https://github.com/ninja-ops-guy/residual-agent-harness/pull/461
https://github.com/ninja-ops-guy/residual-agent-harness/blob/d4027aa261bc3a4e2fa029479498850e7a9a5564/docs/v1/V1_RECOVERY_EVIDENCE_BOUNDARY_REPAIR.md

## Local verification and limits

Linux x86_64 / Python 3.13.5; exact-file source projection, not a full checkout.
Original and published repaired code/test bytes were checked against Git blob
identities. No dependency installation or download was performed.

- Original existing tests: 10 PASS, zero skips.
- New adversarial suite on original #435 source: 23 methods, 31 failed assertions/subtests and 6 errors, exit 1.
- Identical original and new test bytes on repaired source: 33 methods PASS, zero skips, exit 0.
- Initial outer-tool timeout and partial log are retained separately; the same bounded negative suite subsequently completed with failures under a longer outer allowance. No expectation was weakened.

Command:
`python -W error::ResourceWarning -m unittest discover -s tests -p 'test_v1_recovery_evidence*.py' -v`

Source identities:
- original validator blob `9faf9306cf86434bc412142efdbbbdb34703f2fb`;
- corrected validator blob `26dcfadcec681bac6b631237572709224c7d9dae`;
- original tests unchanged `aa0624885b419629ef449128e9bb09a00ede5df5`;
- adversarial tests `ebdd04781e459f4ff93861c59a06609225734a4b`.

The detailed repair note retains source SHA-256 identities and local log hashes.
Synthetic OBSERVED/approval fixture fields are parser test inputs, not real
observations or human approvals. The validator still emits VALIDATION_ONLY;
it does not authenticate approval/profile/index claims or prove operational
measurement provenance. Those acceptance obligations remain independent.

## Exact-head hosted snapshot, not predecessor inheritance

On #461 `d4027aa261bc3a4e2fa029479498850e7a9a5564` at this observation:
- Control Plane `36207173538`: PASS;
- Factory ownership `36207173528`: PASS;
- Clean install `36207173522`: PASS;
- Measured evaluation binding `36207173533`: PASS;
- Qualification-v1 `36207173515`: IN_PROGRESS;
- Command Station `36207173472`: IN_PROGRESS;
- Controller/provider `36207173490`: IN_PROGRESS;
- Maintainer `36207173534`: FAIL at explicit exact-head approval after policy tests passed;
- PR-Agent `36207173506`: FAIL at advisory review after build and secret-presence preflight; publication verification skipped. Root cause not re-inferred from earlier runs.

Fresh results are required for this successor and for the new master-document
head. Nothing is promoted from #435 or an earlier #427 head. No workflow rerun
was requested to chase green. Human review and guarded integration remain open.

## Other stages unchanged by this work

PRE-CANARY: no #423/#445 scope decision, #426 receipt/recovery/concurrency
disposition or PR-G26 evidence was supplied. This pass does not freshly reproduce
#426 or change its recorded finding classification.
CANARY / POST-CANARY: no authorization, execution or procedure change.
PRE-PRODUCTION: PR-G27/PR-G28 and AUD-1/F6 remain governed by their existing
owners and retained prerequisites; no helper or candidate was changed here.
RELEASE: no selected RC, recovery exercise, elapsed soak, tag or release action.
R5 / POST-V1 / RESEARCH: no requirement added to the v1 critical path.

Historical R4.1 qualification remains scoped historical evidence only. No main
push, merge, auto-merge, approval, attestation, frozen-byte mutation, physical F6,
canary, private Seal action, live service/credential/topology change, paid provider
workload, deployment, tag, release or schedule change occurred.
