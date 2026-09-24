# RESIDUAL v1 master readiness checklist

Status: **review-only release-convergence ledger**. This file does not authorize a canary, merge, deployment, release, tag, physical test, or production mutation.

## Snapshot / authority boundary

- Repository main observed for this ledger: `d796f36b75e730a0bab71bdba564206174393719` (tree `39d23b7a8d395664329866d43a3fb9c97e8d83fb`).
- Frozen R4.1 candidate referenced by the overnight lanes: `8701367db6d3202f24b3eb9f4696b0cadf657985`, tree `79bfe6ed1743907065ed44aeb9c460c47527e0c6`.
- The frozen R4.1 candidate is not modified by this branch. Historical R4.1 qualification remains evidence for its exact tested scope; it is not whole-platform production acceptance.
- Seal v2, authoritative `runtime-20260924T025450Z`, original failed evidence/seal, and frozen research experiments are outside this branch.
- `PR Agent` is advisory. Human review/attestation and physical evidence are not inferred from CI.

Allowed status values: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `VERIFIED`, `READY_FOR_REVIEW`, `MERGED_AND_REQUALIFIED`.

## Release-critical dependency order

```text
PRE-CANARY scope/evidence disposition
  -> authorized bounded canary
  -> frozen post-canary evaluation
  -> AUD-1/security convergence + exact physical F6 + independent re-audit
  -> deployment-scope decisions + applicable production qualification gates
  -> exact release candidate + recovery/soak/provenance
  -> human release GO + deployment/rollback window
  -> v1 closure receipt/tag/archive
```

## PRE-CANARY

| ID | Requirement / acceptance criterion | Source / exact head | Classification | Dependencies | Owner | Implementation PR | Test / evidence | Status | Human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-PC-001 | Seal authorization must recompute claims directly from the authoritative manifest; no supplied/derived count may become authority. Independent verifier must reject stale count/digest/unsafe paths. | #415 `3da0d8ec45adf8934b88906462706617aa22831f`; #422 `31dc9c1bf88ee69f417f53c0f4ff5558fc48f645` | observed defect + verified proposed tooling | none | release/evidence | #415, #422 | #415 reports 50-entry derivation and four unit tests; #422 reports 11 adversarial tests; exact-head repository qualification workflows reported green | READY_FOR_REVIEW | review the verifier/tooling; do not alter existing Seal v2 |
| V1-PC-002 | Decide whether the canary threat model requires client-side semantic binding of receipt object, project, operation, actor/payload identity. If required pre-canary, a new successor candidate and fresh qualification are mandatory. | #423 `324a8421205c664cb4cfbfda9582a6e79d43ee64` PR-G32; #426 `494dac7c0702a285c33ceddd3f0237f63ceea425` | reported observed finding / scope decision | V1-PC-001 | owner + canary reviewer | none yet | #426 reports malformed, wrong-project, wrong-operation receipts becoming `ACKED` under synthetic transport substitution; not independently reproduced by this ledger | BLOCKED | explicitly include or exclude this adversary from the bounded canary scope; record rationale |
| V1-PC-003 | Decide whether recovery must verify the stored payload digest before any network action in the bounded canary. If included, mismatch must quarantine/fail closed with zero POST. | #426 `494dac7c0702a285c33ceddd3f0237f63ceea425` | reported observed finding / scope decision | V1-PC-001 | owner + canary reviewer | none yet | #426 reports a tampered stored payload POSTed and later ACKed because recovery did not re-check the stored digest | BLOCKED | scope disposition; successor required if pre-canary |
| V1-PC-004 | Decide whether more than one recovery owner/process is permitted by canary topology. If yes, require fencing before live canary; if no, prove and document single-owner exclusion in preflight. | #426 `494dac7c0702a285c33ceddd3f0237f63ceea425` | reported observed finding / scope decision | V1-PC-001 | owner + canary reviewer | none yet | #426 reports synchronized recoverers each issuing POST after both observed no receipt | BLOCKED | choose threat/topology scope and record enforcement/evidence |
| V1-PC-005 | Canary package must remain refusal-default and be bound to a deployment-specific adapter, expected service baseline, safe evidence destination, independent authorization receipt and exact operator GO. | #412 `2bcfc010c48c8d5d8d8b130ea10b3fb1e67583ef` | missing live/environment evidence | V1-PC-002..004 | canary owner/operator | #412 | package compile/self-tests and manifest checks reported PASS; canary NOT RUN | BLOCKED | supply/review deployment adapter, baseline, destination, authorization receipt and GO |
| V1-PC-006 | Freeze the post-canary verifier before observing canary results; retain authorization-receipt trust anchor independently; evidence producer must emit exact schema. | #413 `466951e63bd8d48d0aba726ef0c0c7d2f8ba4f8c` | verified proposed tooling | V1-PC-005 | independent verifier reviewer | #413 | 9 targeted tests, schemas and deterministic negative controls reported PASS | READY_FOR_REVIEW | review/freeze exact verifier bytes and trust anchor before execution |
| V1-PC-007 | Canary attack corpus remains review evidence; unexecuted R5 candidates/hypotheses must not be promoted to R4.1 defects. Any executed oracle violation becomes an explicit blocker. | #417 `cc7b9558a4c64c721c488bcd50226bfec6d09d31` | qualification planning | V1-PC-002..004 | canary/research reviewers | #417 | 36 deterministic cases; 2 PROVEN, 5 OBSERVED, 26 R5_CANDIDATE, 3 OPEN_HYPOTHESIS | READY_FOR_REVIEW | review corpus classification and keep unexecuted cases off critical path |

## CANARY

| ID | Requirement / acceptance criterion | Source | Classification | Dependencies | Owner | Implementation PR | Evidence | Status | Human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-CAN-001 | Explicit human authorization receipt and GO must bind exact candidate, exact canary procedure, adapter, environment, evidence destination, time window and operator. | #412/#413 | human gate | all V1-PC applicable items | owner/change authority | none | no live authorization retained in repository | BLOCKED | issue authorization only after pre-canary scope is resolved |
| V1-CAN-002 | Execute exactly the bounded R4.1 continuity operation under the frozen procedure: durable intent, one initial POST, induced post-commit/pre-ACK interruption, receipt-first restart reconciliation, bounded time/network actions, no forbidden mutations. | #412 | live evidence | V1-CAN-001 | canary operator | none | NOT EXECUTED | NOT_STARTED | perform separately authorized live canary |
| V1-CAN-003 | Preserve raw canary evidence, pre/post service state, exact network trace, outbox transition, receiver effect count, rollback rehearsal and manifest hashes without rewriting failed evidence. | #412/#413/#418 | evidence requirement | V1-CAN-002 | evidence custodian | none | no live bundle exists | NOT_STARTED | retain evidence even on FAIL/INCOMPLETE |

## POST-CANARY

| ID | Requirement / acceptance criterion | Source | Classification | Dependencies | Owner | Implementation PR | Evidence | Status | Human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-POST-001 | Evaluate the completed bundle with the pre-frozen verifier; disposition must be one of `ROLLBACK_REQUIRED`, `EVIDENCE_INCOMPLETE`, `CANARY_FAILED`, `PROMOTION_ELIGIBLE` with unsafe-state precedence preserved. | #413 | deterministic evaluation | V1-CAN-003 | independent verifier | #413 | verifier tests only; no live bundle | NOT_STARTED | independently run verifier after canary |
| V1-POST-002 | `PROMOTION_ELIGIBLE` is evidence only, not authorization. Any candidate/evaluator byte change invalidates transferred qualification and requires a new identified candidate/review. | #413/#418 | authority boundary | V1-POST-001 | owner/release authority | none | no promotion decision exists | NOT_STARTED | record explicit disposition and next path |

## PRE-PRODUCTION — scope and security convergence

| ID | Requirement / acceptance criterion | Source / exact head | Classification | Dependencies | Owner | Implementation PR | Test / evidence | Status | Human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-PP-001 | Freeze the supported v1 deployment topology/trust boundary and service objectives: loopback/local vs remote exposure, supported proxy/TLS pattern, user/tenant model, supported OS/filesystem/runtime, SLO, RPO and RTO. Production gates are evaluated against this declared scope. | #423 `324a8421205c664cb4cfbfda9582a6e79d43ee64` | missing product authority / scope decision | V1-POST-002 may proceed in parallel for planning | owner + operations | none | audit explicitly reports no authoritative topology/SLO/RPO/RTO | BLOCKED | publish owner-approved scope and objectives; do not silently broaden or narrow to clear gates |
| V1-PP-002 | Select the AUD-1 successor containing F1/F2/F3/F4/F6 plus C1/C2/C3 continuity repairs; exact current head must pass full exact-head CI. | issue #353; #416 current observed head `d41a9428e8667963f85526f44a9616be19ca9d7f` | verified unmerged implementation | none | AUD-1 closure lane | #416 | exact-head Control Plane, Factory ownership, clean install, measured binding, controller/provider, Command Station, Qualification-v1 and Pages reported success; maintainer gate fails because no attestation | READY_FOR_REVIEW | select candidate only after independent technical review |
| V1-PP-003 | Obtain genuine independent human review of C1/C2/C3 and completion-barrier semantics; PR Agent does not satisfy this. | #416 / issue #353 | missing review evidence | V1-PP-002 | independent reviewer | #416 | no submitted PR reviews observed at current head | BLOCKED | independent technical review |
| V1-PP-004 | Qualify the physical F6 helper against the deliberately selected successor rather than silently reusing/retargeting #403 bound to #399. | #403 `118ec3c795ae11c88b68278717fb781f4b059559`; #416 | missing exact-target evidence | V1-PP-002, V1-PP-003 | AUD-1 operator | successor helper required/reconciled | current helper is bound to original #399 bytes | BLOCKED | explicitly reconcile/select target and requalify helper |
| V1-PP-005 | Real-host F6-A: interrupt/recover inside authority window, prove same valid owner continuity with no duplicate authority/invalid transition; retain independent frozen evidence bundle. | issue #353 | required physical evidence | V1-PP-004 | physical test operator | none | not established for #416 successor | BLOCKED | separately authorize/execute physical case A |
| V1-PP-006 | Real-host F6-B: exceed authority window, restore after reassignment, prove old worker/lease/result stays dead; retain separate frozen bundle. | issue #353 | required physical evidence | V1-PP-004 | physical test operator | none | not established for #416 successor | BLOCKED | separately authorize/execute physical case B |
| V1-PP-007 | Mason/LEGION independent read-only re-audit must classify F1/F2/F3/F4/F6 for exact selected bytes and attempt falsification. | issue #353 | independent audit gate | V1-PP-005, V1-PP-006 | Mason/LEGION | none | outstanding | BLOCKED | perform independent re-audit without modifying candidate |
| V1-PP-008 | Fresh exact-head qualification and genuine owner attestation on unchanged selected AUD-1 head. | issue #353/#416 | human + exact-head gate | V1-PP-007 | owner/maintainer | #416 or successor | current technical CI green, owner attestation intentionally absent | BLOCKED | attest only after all preceding evidence |

## PRE-PRODUCTION — production qualification matrix

The #423 audit is a proposal, not automatic proof that every gate applies to every topology. `V1-PP-001` determines applicability. Items already covered by the AUD-1 lane or pre-canary work are deduplicated below rather than counted twice.

| Gate | Acceptance criterion | Classification | Dependency / overlap | Status |
|---|---|---|---|---|
| PR-G01 | Prove bootstrap/operator authority is unreachable to untrusted clients in every supported bind/proxy topology. | security qualification | V1-PP-001; overlaps AUD-1 F1/F3 | IN_PROGRESS |
| PR-G02 | Principal/role/project matrix rejects cross-project confused-deputy operations. | security qualification | V1-PP-001; overlaps AUD-1 F2/F4 | IN_PROGRESS |
| PR-G03 | Rotate/revoke/expire every supported credential during active and queued work with deterministic old-authority rejection. | security qualification | AUD-1 C1 + credential policy | IN_PROGRESS |
| PR-G04 | Secret-taint corpus proves no key/token leakage via APIs, logs, errors, exports, backups or environment. | security qualification | V1-PP-001 | NOT_STARTED |
| PR-G05 | Supported remote topology proves trusted proxy/TLS/certificate validation and downgrade/redirect refusal. | topology/security qualification | V1-PP-001 | BLOCKED |
| PR-G06 | Declare SQLite/filesystem durability assumptions and prove power-loss/WAL/fsync behavior on every supported filesystem. | durability qualification | V1-PP-001 | NOT_STARTED |
| PR-G07 | Versioned encrypted backup/restore contract meets declared RPO/RTO and passes integrity rehearsal. | recovery qualification | V1-PP-001 | BLOCKED |
| PR-G08 | Crash at every durable-state/external-effect boundary; no false success/duplicate unsafe effect. | crash-consistency qualification | R5 fault corpus may supply fixtures | NOT_STARTED |
| PR-G09 | Explicitly support or fail closed for multi-process/multi-host ownership; contention must preserve uniqueness. | concurrency qualification | V1-PC-004; V1-PP-001 | BLOCKED |
| PR-G10 | Required security/operation event schema survives loss injection/redaction/reconciliation. | observability qualification | V1-PP-001 | NOT_STARTED |
| PR-G11 | Log rotation/retention/disk budget and hostile-content/disk-full tests pass. | operations qualification | V1-PP-001 | NOT_STARTED |
| PR-G12 | Low-cardinality service metrics can be recomputed from authoritative state/journal and bound to SLOs. | observability qualification | V1-PP-001 | BLOCKED |
| PR-G13 | End-to-end trace continuity, sampling/loss/clock-skew and secret-leak corpus. | optional/post-v1 unless topology/SLO makes mandatory | V1-PP-001 | NOT_STARTED |
| PR-G14 | CPU/memory/fd/thread/process/disk/network/model/install/job budgets fail safely under exhaustion. | resource qualification | V1-PP-001 | NOT_STARTED |
| PR-G15 | Enumerate every blocking operation and prove a global upper bound/cancellation path compatible with SLO. | timeout qualification | V1-PP-001; AUD-1 C2/C3 contributes | IN_PROGRESS |
| PR-G16 | System-wide retries are bounded with backoff/jitter and no amplification/retry storm. | reliability qualification | V1-PP-001 | NOT_STARTED |
| PR-G17 | Per-principal/IP/operation rate-limit policy and bypass/recovery tests where externally reachable. | security/availability qualification | V1-PP-001 | BLOCKED |
| PR-G18 | ENOSPC/inode/quota/read-only faults at DB/artifacts/logs/evidence fail closed with preserved forensic state. | durability qualification | #426 explicitly leaves real ENOSPC open | NOT_STARTED |
| PR-G19 | SQLite page/WAL/schema corruption corpus triggers bounded quarantine/preservation/restore rather than unsafe network actions. | durability/recovery qualification | #426 reports truncated/corrupt cases only partially explored | NOT_STARTED |
| PR-G20 | Reproduce supported install/start/health/isolation from exact immutable release artifact on clean target host. | deployment qualification | V1-PP-001 | NOT_STARTED |
| PR-G21 | N/N-1 code+data rollback with in-flight work preserves audit/effect uniqueness and passes rehearsal. | rollback qualification | V1-PP-001 | NOT_STARTED |
| PR-G22 | Old/new compatibility matrix and unknown-major fail-closed behavior for persisted schemas/protocols. | upgrade qualification | V1-PP-001 | NOT_STARTED |
| PR-G23 | Boot-time complete config validation rejects unknown/typo/unsafe cross-field deployment states. | configuration qualification | V1-PP-001 | NOT_STARTED |
| PR-G24 | Authenticated/audited stop, drain, quarantine, resume and break-glass controls are tested. | operator qualification | V1-PP-001 | NOT_STARTED |
| PR-G25 | Action-to-audit completeness plus tamper/truncation/tail-deletion detection. | audit qualification | evidence-authority work contributes | NOT_STARTED |
| PR-G26 | Direct-source evidence recomputation and frozen verifier before canary/release. | evidence integrity | V1-PC-001 | READY_FOR_REVIEW |
| PR-G27 | Actions/dependencies/artifacts have SBOM, signatures/provenance and tamper verification; remove unjustified floating trust where release-critical. | supply-chain qualification | release candidate | NOT_STARTED |
| PR-G28 | Reproducible/offline release build from hash-locked dependency set. | supply-chain qualification | release candidate | NOT_STARTED |
| PR-G29 | CI lanes perform capability preflight and fail closed when required capability is absent; preserve first failure and environment identity. | CI qualification | #425 `052065c76955f772bb2ac6c49fe67fcc66ecfc20` proposes ENV-G01 | READY_FOR_REVIEW |
| PR-G30 | Incident drills cover credential leak, corruption, runaway work, compromise and evidence breach. | operational qualification | V1-PP-001 | NOT_STARTED |
| PR-G31 | Host/region-loss restore meets RPO/RTO and preserves fencing/uniqueness; if unsupported, topology must explicitly exclude the claim. | DR qualification | V1-PP-001 | BLOCKED |
| PR-G32 | Exact receipt binding before local ACK. | receipt safety | V1-PC-002 | BLOCKED |
| PR-G33 | Durable stale/indeterminate/quarantined state and authorized operator disposition; clock anomalies cannot imply resend/success/delete. | state-model qualification | R5 program | NOT_STARTED |

## RELEASE / RC CLOSURE

| ID | Requirement / acceptance criterion | Source | Dependencies | Status | Human action |
|---|---|---|---|---|---|
| V1-REL-001 | Reconcile and integrate only release-critical PRs after exact-head review/qualification; after each merge require authoritative resulting-main qualification. No stale-head evidence transfer. | issue #353, repository governance | all applicable pre-production blockers | BLOCKED | guarded merges remain separate owner actions |
| V1-REL-002 | Define exact RC commit/tree from resulting main and create immutable build artifacts, SBOM, provenance and hashes; no rebuild between qualified RC and final tag. | #418 `695e35733f75d0b4bd5f02941aa29ac9fd57a987` | V1-REL-001, PR-G27/28 | NOT_STARTED | review corrected release schema before use |
| V1-REL-003 | Correct release-receipt schema so final v1 candidate/tag bind to the selected post-convergence RC, not permanently to frozen R4.1 `8701367d...`. R4.1 identity belongs in canary provenance, not as the immutable final release commit unless owner explicitly chooses that exact code as v1. | #418 current schema | V1-REL-002 | BLOCKED | release-ops lane should revise schema before acceptance |
| V1-REL-004 | Clean-environment install/recovery from exact RC artifact passes supported platform matrix with retained evidence. | #418 + PR-G20 | V1-REL-002 | NOT_STARTED | execute after RC selection |
| V1-REL-005 | Backup/restore and rollback rehearsal pass against exact RC/data schema; previous artifact and recovery point retained. | #418 + PR-G07/G21 | V1-REL-002 | NOT_STARTED | operations/data-owner authorization |
| V1-REL-006 | Required elapsed burn-in/soak window completes without fabricating or shortening elapsed time; failure evidence retained. | release policy / #418 | V1-REL-004/005 | NOT_STARTED | approve exact soak duration and environment |
| V1-REL-007 | Release manager/maintainer/security/operations/product approvals produce explicit GO/NO_GO/ROLLBACK/EVIDENCE_INCOMPLETE decisions bound to exact RC/evidence. | #418 | all applicable release gates | NOT_STARTED | human approvals |
| V1-REL-008 | Deploy exact approved artifact using staged checklist; observe guardrails and rollback window; no automatic promotion. | #418 | V1-REL-007 | NOT_STARTED | deployment authorization |
| V1-REL-009 | Complete release receipt/evidence archive; verify independent copy; final signed `v1.0.0` references exact qualified RC without rebuild. | #418 | V1-REL-008 | NOT_STARTED | release closure authorization |

## R5 / POST-v1

R5 planning does not automatically block the bounded R4.1 canary or v1. Scope-disposition items V1-PC-002..004 may promote a subset into pre-v1 requirements.

| ID | Requirement | Source | Status |
|---|---|---|---|
| V1-R5-P0 | Evidence authority, deterministic fault/corpus infrastructure, independent phase convergence. | #410 `49b625b87ba6aea5e62c04af2afe89ebc7ca4266`; #419 `6c417103417b89d6adba1e880f919c20ba98f7dc`; #421 `5d8b9a41671201ac0c0a822ed5d0e5a9124c30ea` | READY_FOR_REVIEW |
| V1-R5-P1 | Versioned protocol + authenticated request-bound receipt authority. | #410/#419 | NOT_STARTED |
| V1-R5-P2 | Fenced recovery/reconciliation with single durable authority. | #410/#419/#426 | NOT_STARTED |
| V1-R5-P3 | Crash durability, corruption handling, explicit indeterminate/quarantine/stale disposition. | #410/#419/#426 | NOT_STARTED |
| V1-R5-P4 | Multi-process/topology/observability/lookup/lifecycle hardening. | #410/#419 | NOT_STARTED |
| V1-R5-P5 | Formal claim/convergence qualification and accepted immutable phase receipts. | #410/#419 | NOT_STARTED |

Post-v1-only research/features such as APF/RRI-005 (#407), inference-aware routing (#406), measured research lanes and other optional adapters are not on the v1 critical path unless a verified production blocker explicitly promotes them.

## RESEARCH / METHODS (not release gates by default)

| ID | Requirement | Source | Status |
|---|---|---|---|
| V1-RES-001 | Preserve R4/R4.1 chronology with corrected evidence cardinality: any `44/44` derived-seal wording must be corrected or explicitly marked superseded by authoritative 50-entry manifest evidence before publication/merge. | #411 `1e2592bfc81dfe94d0f39332ebd451862680cab4`; #415 | BLOCKED |
| V1-RES-002 | Maintain claim/evidence matrix with alternatives, ablations, replication and literature review; do not claim novelty from architecture alone. | #424 `352029e88573023cbe81a7288601189bd93311c7` | READY_FOR_REVIEW |
| V1-RES-003 | Maintain reproducibility registry without relabeling retrospective observations as preregistered. | #420 `b36b15f1b161ff8d7a913ca47f8a3bea3fab660c` | READY_FOR_REVIEW |
| V1-RES-004 | Preserve test-environment drift as an explicit finding: broad-suite count did not reproduce exactly and missing loopback/crypto/bubblewrap capabilities must be machine-recorded before interpreting failures. | #425 `052065c76955f772bb2ac6c49fe67fcc66ecfc20` | READY_FOR_REVIEW |

## Current release blockers / owner queue

1. **Canary scope decision:** receipt semantic binding, recovery digest verification, and concurrent recovery fencing reported by #426 require explicit bounded-canary scope disposition before GO.
2. **AUD-1 successor:** #416 exact head has current technical CI success, but no independent human review, no successor-bound physical F6-A/F6-B, no Mason/LEGION re-audit and no genuine owner attestation.
3. **Deployment contract:** v1 topology/trust model and SLO/RPO/RTO are not yet authoritative; this determines which #423 production gates apply.
4. **Release schema:** #418 currently hard-binds final `v1.0.0` candidate/tag to the frozen R4.1 candidate. That must be intentionally reconciled with the actual post-convergence RC before release tooling is accepted.
5. **Canary itself:** not executed; post-canary disposition is therefore not available.

## Readiness statement

No exact percentage is asserted. Current evidence supports: R4.1 has a historical exact-scope `READY_FOR_CANARY` qualification; canary execution remains blocked on explicit scope/authority prerequisites; production v1 remains blocked on AUD-1 physical/independent closure, deployment-scope authority, applicable production qualification, exact RC recovery/soak/provenance and human release authorization.
