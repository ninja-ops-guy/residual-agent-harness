# RESIDUAL v1 master remaining-work list

**Current review-only view: 2026-09-26. Single master PR: #427. No release authority.**

This is the current entry point for v1 convergence, replacing the stale #416-era summary in this file. Historical observations are preserved at [the immutable preceding snapshot](https://github.com/ninja-ops-guy/residual-agent-harness/blob/fb63b4b4fd1dedb1db72f14183f558833ab027b3/docs/v1/V1_MASTER_READINESS.md) and in the unchanged `V1_MASTER_READINESS_DELTA*.md` files. This refresh changes planning/read-model state, not frozen experimental evidence, an evaluator, acceptance criteria, or execution authority.

## Baseline and status rules

- Accepted main: `d796f36b75e730a0bab71bdba564206174393719`.
- Master predecessor read immediately before this update: `fb63b4b4fd1dedb1db72f14183f558833ab027b3`.
- Frozen R4.1 candidate: `8701367db6d3202f24b3eb9f4696b0cadf657985`; tree `79bfe6ed1743907065ed44aeb9c460c47527e0c6`. Reference only. Historical 17/17 READY_FOR_CANARY is not v1 production qualification or canary authorization.
- Seal v2, authoritative `runtime-20260924T025450Z`, original failed evidence, frozen research and live hosts/services are unchanged and unavailable as execution targets in this task.
- Status vocabulary: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `VERIFIED`, `READY_FOR_REVIEW`, `MERGED_AND_REQUALIFIED`. Each row's status applies only to its stated acceptance criterion. A reviewable implementation does not complete its parent operational gate.
- Sources marked **retained** below are previous exact-head records, not newly executed or independently requalified in this pass. Author reports, submitted reviews, owner decisions, hosted tests and private operational evidence remain distinct.
- No percentage substitutes for satisfied applicable gates. No row is promoted to MERGED_AND_REQUALIFIED here.
- The main ruleset `23436488` was read: strict tests/qualify/python 3.11-3.13, browser, docker, factory-ownership and maintainer-approval contexts remain required. Repository review-count settings do not waive the separately required human/security review process. No rule or protected pin was changed.

## Exact source registry

Aliases in the tables bind requirements and evidence to these exact sources, not to a moving branch name.

| Alias | Exact source | Interpretation |
|---|---|---|
| AUDIT | #423 `324a8421205c664cb4cfbfda9582a6e79d43ee64`, `docs/research/PRODUCTION_READINESS_MATRIX_2026-09-23.md` | Original static production audit; PR-G01..33 proposed applicability depends on approved scope |
| FAULTS | #426 `494dac7c0702a285c33ceddd3f0237f63ceea425`, `docs/research/R4_OFFLINE_FAULT_SPACE_2026-09-23.md` | Retained disposable/synthetic receipt, recovery-digest and concurrent-recovery observations; not independently reproduced in this pass |
| CLAIMS | #445 `9eba077817720021174671ba1652b59fb801b670` | Proposed claims/CV lifecycle; later owner scope inputs reconcile subsets, not wholesale approval |
| MATRIX | #465 `d9e16bf92ba59b3d778666e11b0a948303b9475e`, `docs/v1/V1_RELEASE_MATRIX.md` and `V1_OWNER_DECISION_PACKET.md`; comment `5843059963` | Recorded owner-supplied platform/provider-class matrix and distribution direction; specific remaining decisions below |
| DOCKER | #469 `935498ecd42982bc682d7ed69b562c642b74a8fe`, tree `8d8ecb2970d3dc2cf304ba8c8c6997a05b45370b`; owner comment `5842785986` | Approved bounded Docker/AUD-1 direction FOR subsequent immutable selection/helper reconciliation; not an inferred completed selection or F6 GO |
| AUD1 | Issue #353 and DOCKER; frozen #403 `118ec3c795ae11c88b68278717fb781f4b059559` | Existing Closure single writer owns security/candidate/helper work and physical qualification |
| OLDHELPER | #455 `a2567103c7e634310d696e421692fa1f86624e3b`, bound to #448 `943c77a28ada1bc3931408c5f9b40d40c25eb2dc` | Prior qualified/approved helper; DOCKER owner disposition forbids using its historical binding for current physical F6 |
| PROFILE | #472 `9d9740d3d6d551d1861214ea9f835dc484726ee5`, tree `3e48689ce6a79f56c58d6a391308fbaf21f4fcdc` | Now published, hosted-qualified and non-draft; original #432 `f6487c8430f03e930c3ae22c99f41117d310372e` remains unchanged |
| SUPPLY | #468 `f30a1e16f14d92b623770b3866b5c249d9dee263`, stacked on #467 `7aa21a7b2cd3e49c27aba2d360380a36cd7f266e` | Now non-draft; structural/transitive pinning chain, not completed provenance acceptance |
| SEAL | #447 `ad524c461aa60426695f226f541e172c557b8e98`, parent #443 `d2c8bb907da0c51f0bd56c9f5cb0114816b93205` | Bounded JSON/containment/cardinality tooling, not private semantic/package-closure verification |
| LOCK | #444 `78c34d3d7fde7b5edf8488a0842acb96270cfb95` | Python lock grammar tooling only; no authoritative transitive lock/offline build |
| RECOVERY | #461 `d4027aa261bc3a4e2fa029479498850e7a9a5564`; source #435 `378207e511550532dbba60e8d4ae489666aa6c09` | Reviewable numeric/JSON recovery-evidence validator successor; no recovery exercise |
| ARCHIVE | #458 `e8894c443936710b86efc85e9cbcc29a5f70840e`, parent #457 `2b75b42cd8cf1a7f13eac64a77d86ddfb619d169` | Retained promotion-invariant archive-confinement repair candidate; separate review/scope/current-main integration needed |
| CANARY | #412 `2bcfc010c48c8d5d8d8b130ea10b3fb1e67583ef` | Retained refusal-default procedure proposal; not an executed canary |
| POST | #413 `466951e63bd8d48d0aba726ef0c0c7d2f8ba4f8c` | Retained post-canary verifier proposal; independent freeze required before use |
| RELEASE | #418 `695e35733f75d0b4bd5f02941aa29ac9fd57a987`; #428 `e666c7e746d159b63b0a9fab034e2d1419c7717e` | Retained release tooling and RC-binding successor; no live release receipt |
| OPS | #434 `76a2a69fa6c7c2959108de2369796a755d59ea84`; #430 `2dd7f5c04b3fff51ecb2646443d6f5120b12043b` | Retained incident-plan and environment-preflight tooling, not operational acceptance |
| VERSION | #466 `edc3e47ea14de77ce3ca7140bd34e729f4cea9bd`, successor to #429 `9d38d87df9bfa5004d3eb5d7144e60ef1ced56f7` | Retained review-ready 0.5.0 metadata normalization; not a 1.0.0 release |

## Material work completed in this pass

### PROFILE: published and hosted-qualified, not an approved profile

#472 was opened from the existing repair branch rather than creating a duplicate implementation. After exact-head CI completed it was made ready for review; source/base stayed unchanged and submitted reviews were zero. Comment `5848229066` records the terminal evidence.

| Technical workflow | Exact-head run | Result |
|---|---|---|
| Qualification-v1 | 36258053638 | PASS |
| Command Station | 36258053839 | PASS |
| Controller/provider | 36258053501 | PASS |
| Clean install | 36258053603 | PASS |
| Factory ownership | 36258053489 | PASS |
| Control Plane | 36258053479 | PASS |
| Measured binding | 36258053667 | PASS |

Deterministic artifact `10911516718` was downloaded and independently hashed: SHA-256 `fb529d9250c7ddeb6ca4a976a50cab9de4b327459d8b9c331244fc7126832435`, matching GitHub metadata. Its source envelope binds PROFILE HEAD/tree, clean tracked source, Ubuntu/X64 and Python 3.12.14. The JUnit artifact includes **19 deployment-profile tests with zero failures, errors or skips**, including all three inactive padded-UNDECIDED controls. Hosted command: `python -m pytest tests --ignore=tests/qualification -q --junitxml=runs/qualification-v1/deterministic.xml`.

The retained first-failure predecessor `20adc626cf7200afc101d2cb3c9ea0f078e7b27d` and prior negative-control replay are not rewritten. No local product suite was newly executed in this pass. Maintainer run `36258053581` fails at explicit exact-head approval after policy tests pass. PR-Agent `36258053522` fails at advisory execution after build/secret preflight; publication verification is skipped. Its model-call cause was not re-established here.

### SUPPLY: review state unblocked, provenance still open

#468 was changed from draft to ready for review with unchanged HEAD/base. Action Pin Gate `36211835639`, Qualification-v1 `36211835517`, Command Station `36211835404`, controller/provider `36211835438`, clean install `36211835650`, Factory ownership `36211835469`, Control Plane `36211835363`, and measured binding `36211835399` all have successful exact-head results. Submitted reviews were zero.

PR-Agent `36211835483` pulled the pinned digest and completed its command, but its substantive-publication verification failed. Successful command exit is not a published review. The upstream image source/build-attestation acceptance is still open. The image digest, not the tag spelling, supplies content identity.

## Consolidated owner decision packet

This is the residual-action view of MATRIX's existing decision packet, not a competing scope proposal. No unresolved value is chosen by an agent and no approval token is supplied here.

| Decision | Already recorded input | Exact remaining owner/operations action | Unlocks |
|---|---|---|---|
| D1 / Docker | DOCKER approves a single trusted local Compose host, loopback publication, trusted daemon/project-network participants; no public/Kubernetes/multi-tenant/HA-container claim | Closure owner records explicit immutable candidate selection, preserves helper hardening, reconciles and qualifies the new helper, then requests separate F6 GO | AUD1 helper/F6 chain |
| D2 / distribution | MATRIX records Apache-2.0 Open Core plus reserved/proprietary commercial layers | Accept final boundary and verify exported license/NOTICE, reserved-code exclusion and artifact provenance; record private commercial repository/terms privately | Public artifact/license closure, not a new choice of business model |
| D3 / supported matrix | Windows x64/Linux x64 native; Linux Docker Engine/Docker Desktop Windows/NVIDIA overlay; desktop Chromium/Firefox/automated WebKit; local Ollama; one real hosted-provider success required. Native macOS and Docker Desktop macOS are v2; physical-iPhone heavyweight WebVM unsupported | Name each admitted hosted provider/model/deployment; finalize exact OS/Python/filesystem/artifact/extras identities needed for locking/builds. Authorize credential use and a bounded paid workload separately, never post secrets | Release matrix completion, LOCK, exact-RC provider acceptance |
| D4 / Shared Comms | Separate research/integration by default is a proposed boundary; no confirmed enforced v1 exclusion is established here | Explicitly INCLUDE and repair/qualify applicable FAULTS findings, or EXCLUDE with release/configuration/entrypoint enforcement and negative tests. Map the old canary's applicability explicitly; do not silently cancel or repurpose it | V1-PC-002..004 and applicable canary gates |
| D5 / operations | No complete approved operational profile located in the inspected sources | Supply availability/SLO, recovery bound, RPO/RTO, backup schedule/retention, supported durability/storage semantics, disk/log/evidence budgets, host/region-loss claims, exact soak environment/workload/duration/cadence/reset rules, and named incident/release/evidence owners | V1-PP-001, operational acceptance and final release |
| Build-input provenance | Docker is supported; LOCK covers Python grammar only | Approve immutable base-image identity and reproducible/authenticated OS-package source policy; authorize trusted transitive resolution/build environment and later offline build comparison | PR-G27/28; no snapshot policy or digest is invented |

The proposed 72-hour soak in CLAIMS is not an adopted duration. Required physical/provider/operational work remains separately authorized. An owner-approved supported platform is not yet a qualified platform.

## Dependency order and ownership

Preparation and review can proceed in disjoint lanes. No optional research lane must finish before release triage. The physical chain is owned entirely by the existing RESIDUAL v1 Closure task:

`DOCKER immutable selection -> new qualified helper -> separate F6 GO -> distinct F6-A/F6-B bundles -> Mason/LEGION read-only re-audit -> exact-head qualification/disposition -> separately authorized integration -> resulting-main qualification`.

In parallel: resolve D3/D4/D5 and build inputs, review PROFILE/SEAL/SUPPLY/LOCK/RECOVERY, and resolve applicable archive and license boundaries. Canary applicability/procedure/authority must be explicitly disposed before execution; no predeclared criterion changes in this ledger. Exact-RC operational gates occur after RC identity exists, not as circular prerequisites to selecting that identity. CLAIMS' proposed lifecycle remains `RC_SELECTED -> RC_QUALIFIED -> SOAK_VERIFIED -> RELEASE_AUTHORIZED`.

## PRE-CANARY

Each Source alias refers to the exact registry above. None means no implementation/evidence exists in this ledger, not proof of its absence elsewhere.

| ID | Acceptance criterion | Source | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-PC-001 | Freeze reviewed independent verifier and recompute authoritative seal claims, package membership and semantic/provenance bindings from immutable direct sources | AUDIT; SEAL | missing evidence | reviewed verifier; trusted private snapshot | release/evidence reviewer | #447/#443 lineage | Bounded tooling only; no private verification executed here | BLOCKED | Select verifier, authorize private read-only verification and accept sanitized evidence/hashes |
| V1-PC-002 | Receipt object/type/project/operation/actor/payload binding is proven before ACK, or capability exclusion is approved and enforced | FAULTS; AUDIT PR-G32; MATRIX D4 | reported finding | D4 scope; selected source | owner plus comms/canary reviewer | none selected | Synthetic false-ACK reports retained; require missing versus explicit-null and cross-binding negative controls | BLOCKED | Decide applicability without downgrading observed risk; assign disjoint successor if applicable |
| V1-PC-003 | Recovery rejects stored-payload digest mismatch before network actions, or approved exclusion is demonstrably enforced | FAULTS | reported finding | D4 scope; selected source | comms/recovery owner | none selected | Retained tampered-payload POST; require isolated zero-POST mismatch control | BLOCKED | Approve disposition and applicable repair/test scope |
| V1-PC-004 | One durable recovery authority is enforced; overlapping recoverers cannot issue unsafe duplicate POST; unsupported topology must be rejected | FAULTS | reported finding | D4 scope; process/topology contract | comms/recovery owner | none selected | Two synchronized POSTs reported; Station exclusivity is not automatically an outbox-recovery proof | BLOCKED | Require isolated ownership/fencing controls or verified exclusion |
| V1-PC-005 | Applicable canary package is refusal-default and bound to approved adapter, service baseline, evidence destination and candidate | CANARY | missing evidence | V1-PC-001..004 | canary owner/operator | #412 or reviewed successor | Retained package tests only; no live adapter/baseline acceptance here | BLOCKED | Approve exact applicability and operator handoff before GO |
| V1-PC-006 | Independent post-canary evaluator and authorization trust anchor are frozen before observing results | POST | missing evidence | applicable V1-PC-005 schema/procedure | independent verifier reviewer | #413 | Retained nine-test proposal; no current freeze receipt | READY_FOR_REVIEW | Review/freeze exact bytes; changes require a distinct proposal |
| V1-PC-007 | Corpus classifications remain evidence-bound; unexecuted R5 hypotheses do not become release defects | #417 cc7b9558a4c64c721c488bcd50226bfec6d09d31 | optional hardening | applicable canary scope | corpus/research reviewer | #417 | Retained corpus, not newly executed | READY_FOR_REVIEW | Review only applicable observations; do not wait for every research case |

## CANARY

| ID | Acceptance criterion | Source | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-CAN-001 | Explicit GO binds candidate/procedure/evaluator/adapter/environment/operator/window/destination | CANARY; POST | missing evidence | applicable V1-PC gates | owner/change authority | none | No applicable current authorization in this pass | BLOCKED | Issue separate authorization after prerequisite acceptance |
| V1-CAN-002 | Execute only the frozen bounded continuity procedure; retain failed attempts as failed | CANARY | missing evidence | V1-CAN-001 | canary operator | frozen accepted procedure | Not executed by this task | NOT_STARTED | Execute only after GO; no silent shortening or altered oracle |
| V1-CAN-003 | Retain raw traces, state transitions, effect counts, rollback evidence and manifest hashes without private-data publication | CANARY; POST; RELEASE | missing evidence | V1-CAN-002 attempt | evidence custodian | accepted evidence collector | No current bundle inspected | NOT_STARTED | Preserve immutable private bundle even on FAIL/INCOMPLETE |

## POST-CANARY

| ID | Acceptance criterion | Source | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-POST-001 | Frozen verifier evaluates the retained bundle with unsafe-state precedence and typed failure/incomplete/promotion-eligible outcomes | POST | missing evidence | V1-CAN-003 | independent verifier | #413 or selected successor | Tooling tests are not live evaluation | NOT_STARTED | Run independently on the authorized bundle |
| V1-POST-002 | Evidence disposition is recorded separately from promotion authority; changed bytes invalidate affected evidence | POST; RELEASE | missing evidence | V1-POST-001 | release owner | disposition record | None for current path | NOT_STARTED | Explicitly accept/reject next step; no automatic promotion |

## PRE-PRODUCTION: profile, security and focused implementations

| ID | Acceptance criterion | Source | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-CLAIMS-001 | Current claims are reconciled with recorded D1-D3 decisions and remaining D3/D4/D5 values, then explicitly approved | CLAIMS; MATRIX; DOCKER | scope decision | owner decision packet | owner/operations | #445/#465 inputs | Partial recorded scope is not complete claims approval | BLOCKED | Approve exact reconciled revision without weakening promises to ship |
| V1-PP-001 | Complete topology/trust/runtime/durability/SLO/RPO/RTO/retention/soak profile is approved and content-bound | AUDIT; MATRIX; PROFILE | scope decision | V1-CLAIMS-001; D3/D4/D5 | owner/operations | #472 tooling; profile still pending | Supported broad matrix recorded, actual full profile absent | BLOCKED | Supply/approve unresolved values and their evidence contract |
| V1-PP-DP-PLACEHOLDER-05 | Inactive optional fields cannot hide trimmed UNDECIDED; original parser/unknown-field controls remain effective | PROFILE; first failure 20adc626cf7200afc101d2cb3c9ea0f078e7b27d | observed finding | human implementation review | repository release-preparation | #472 | Fresh hosted 19 tests PASS and seven technical workflows PASS; no human review | READY_FOR_REVIEW | Review exact repair; reconcile #432 overlap before integration |
| V1-PP-002 | Immutable AUD-1 candidate SHA/tree is explicitly selected under the approved Docker direction | DOCKER; AUD1 | missing evidence | exact-head technical/security disposition | existing Closure single writer and owner | #469 | Direction approved; selection/helper steps expressly still required | IN_PROGRESS | Record exact immutable selection, not inferred from CI or this list |
| V1-PP-003 | Required exact-head technical/security review and any explicitly scoped owner review-process disposition are retained | AUD1; DOCKER | missing evidence | V1-PP-002 selected bytes | security reviewer/owner | #469 lineage | Owner direction is not independent third-party review; prior-head reviews do not transfer automatically | BLOCKED | Complete governed review; disclose any authorized compensating process precisely |
| V1-PP-004 | New #403-lineage helper atomically binds selected candidate SHA/tree and preserves later evidence-hardening fixes | AUD1; OLDHELPER; DOCKER | missing evidence | V1-PP-002, V1-PP-003 | existing Closure single writer | new helper required | No #469-bound helper discovered; old #455 target cannot be used | BLOCKED | Review/requalify successor; then obtain separate exact-identity physical GO |
| V1-PP-005 | Real F6-A proves recovery inside unchanged authority window with valid owner continuity and no duplicate authority | AUD1 | missing evidence | V1-PP-004; separate GO; live preflight | physical operator | selected helper | No physical A bundle inspected | BLOCKED | Provide exact launch witness, owned disposable task and transport/runner evidence; execute separately |
| V1-PP-006 | Real F6-B proves old worker/lease/result remains dead after outside-window loss and reassignment | AUD1 | missing evidence | V1-PP-004; separate GO; live preflight | physical operator | selected helper | No physical B bundle inspected | BLOCKED | Retain a distinct B bundle; do not manipulate state to manufacture expected outcome |
| V1-PP-007 | Independent read-only re-audit attempts falsification and classifies F1/F2/F3/F4/F6 on exact selected bytes | AUD1 | missing evidence | V1-PP-005, V1-PP-006 | Mason/LEGION | audit receipt, not implementation | Post-F6 evidence absent | BLOCKED | Perform re-audit without changing candidate; no agent report substitutes for a required human gate |
| V1-PP-008 | Final unchanged-head qualification and genuine owner disposition precede guarded integration | AUD1 | missing evidence | V1-PP-007 | owner/maintainer | selected successor | Earlier technical CI is not post-F6 acceptance | BLOCKED | Review final evidence; attest only with the required authority |
| V1-PC-R4-02-B1 | Archive confinement remains invariant across staging/promotion, including TAR/TAR.ZST; applicable v1 source is integrated and requalified | ARCHIVE | reported finding | scope disposition; independent review | archive security owner | #458 stacked proposal | Retained technical repair/negative controls; not re-executed here | BLOCKED | Decide applicable trust boundary, then reviewed current-main successor; no edit to frozen research |
| HOSTED-PROVIDER-01 | Each admitted hosted target completes real candidate-to-verifier-to-receipt success on exact RC | MATRIX | missing evidence | named provider/model/deployment; V1-REL-002; separate budget/credential authorization | provider qualification lead | admitted existing adapter | No real provider workload executed here | BLOCKED | Select target and authorize bounded execution separately; never post credentials |
| LICENSE-ARTIFACT-01 | Exported public artifact carries correct license/NOTICE and excludes reserved implementation, with manifest/SBOM binding | MATRIX D2 | missing evidence | reviewed final open-core boundary; artifact identity | owner/legal/provenance reviewer | #442 or selected successor | MATRIX reports progress; no new independent private-repository or legal verification here | BLOCKED | Accept final boundary and private commercial record without publishing commercial code |

## PRE-PRODUCTION: complete PR-G01..PR-G33 audit inventory

These are **parent acceptance gates**, not counts of PRs. Every row inherits exact requirement source AUDIT; referenced aliases supply implementation/evidence. Applicability is UNRESOLVED unless an approved source explicitly resolves it. NONE in Implementation means none selected in this master view. Optional or unsupported-scope items are not automatically release blockers, and observed risks cannot be made optional merely to clear a gate. Operational rows needing an RC are evaluated after V1-REL-002; they are not prerequisites to their own RC identity.

| ID | Acceptance criterion | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|
| PR-G01 | Untrusted clients cannot obtain bootstrap/operator authority in supported topology | missing evidence | V1-PP-001; AUD1 | Closure/security | #469 lineage | Candidate tests contribute; final topology evidence incomplete | IN_PROGRESS | Accept supported-topology negatives |
| PR-G02 | Principal/role/project checks reject cross-project confused-deputy operations | missing evidence | V1-PP-001; AUD1 | Closure/security | AUD1 lineage | Candidate regressions, not final RC acceptance | IN_PROGRESS | Review authority matrix and final evidence |
| PR-G03 | Supported credential rotation/revocation/expiry rejects old authority during active/queued work | missing evidence | credential policy; AUD1 | Closure/security | AUD1 lineage | C1-C6 retained tests contribute | IN_PROGRESS | Approve policy and exercise evidence |
| PR-G04 | Secret-taint controls cover APIs/logs/errors/exports/backups/environment | missing evidence | V1-PP-001 | security qualification | NONE selected | Full supported-surface corpus missing | NOT_STARTED | Approve scope and inspect retained redaction evidence |
| PR-G05 | Admitted remote transport validates TLS/certificates/proxy trust and rejects downgrade/redirect abuse | scope decision | transport profile | network/security | NONE selected | Local Docker decision does not approve arbitrary remote proxying | BLOCKED | Name admitted transport; require applicable negatives |
| PR-G06 | Declared SQLite/WAL/fsync/filesystem assumptions withstand required crash/power-loss cases | missing evidence | durability profile; V1-REL-002 | storage/qualification | NONE selected | FAULTS does not prove real fsync/power-loss durability | NOT_STARTED | Approve filesystem/guarantee set and separate tests |
| PR-G07 | Encrypted application-consistent backup/restore satisfies approved RPO/RTO with integrity evidence | missing evidence | D5; V1-REL-002 | recovery/operations | RECOVERY | Validator is reviewable; actual exercise missing | BLOCKED | Authorize exact-RC recovery exercise and independent evidence acceptance |
| PR-G08 | Crashes at durable-state/external-effect boundaries cannot produce false success or unsafe duplicates | missing evidence | applicable effect inventory | runtime/qualification | NONE selected | Scoped CI and FAULTS contribute; complete boundary matrix missing | NOT_STARTED | Approve bounded failure campaign |
| PR-G09 | Supported process/host ownership is unique or unsupported modes are rejected before mutation | missing evidence | V1-PP-001; V1-PC-004; AUD1 | runtime/qualification | AUD1 lineage | Station ownership does not prove every recovery owner path | IN_PROGRESS | Accept final ownership scope and independent controls |
| PR-G10 | Required security/operation events survive loss/redaction/reconciliation | missing evidence | audit/event profile | observability owner | NONE selected | Complete supported-event contract not accepted | NOT_STARTED | Approve required event set and loss controls |
| PR-G11 | Log rotation/retention/disk budgets survive disk-full and hostile-content cases | missing evidence | D5 storage/retention | operations owner | NONE selected | Accepted exact-RC evidence missing | NOT_STARTED | Set budgets and authorize bounded tests |
| PR-G12 | Declared service SLO metrics are recomputable from authoritative state/journal | scope decision | D5 SLO | operations/metrics | NONE selected | SLO undefined | BLOCKED | Define objective and evidence measurement |
| PR-G13 | If promised, trace continuity/sampling/loss/skew/secret controls pass | optional hardening | explicit trace/SLO claim | observability owner | NONE selected | Post-v1 unless approved scope makes applicable | NOT_STARTED | Decide applicability; do not delay v1 for an unclaimed feature |
| PR-G14 | CPU/memory/fd/thread/process/disk/network/model/install/job exhaustion fails safely | missing evidence | resource profile | runtime/qualification | NONE selected | Full profile-bound matrix missing | NOT_STARTED | Approve limits and safe test fixtures |
| PR-G15 | Blocking operations have bounded completion/cancellation compatible with the declared objective | missing evidence | D5 recovery bound; AUD1 | runtime/qualification | AUD1 contributes | Bounded worker/control tests are partial evidence | IN_PROGRESS | Accept full applicable timeout inventory |
| PR-G16 | Retry budgets/backoff avoid unbounded amplification under faults | missing evidence | retry/service profile | runtime/qualification | NONE selected | Scoped worker proofs not full-system acceptance | NOT_STARTED | Approve applicable retry matrix |
| PR-G17 | Externally reachable/multi-user operations meet approved rate-limit and bypass requirements | scope decision | V1-PP-001 | security/operations | NONE selected | Do not infer Internet-facing scope from local Docker support | BLOCKED | Resolve applicability; require controls where reachable |
| PR-G18 | ENOSPC/inode/quota/read-only faults preserve safety and forensic state | missing evidence | supported storage; bounded test authority | storage/qualification | NONE selected | FAULTS leaves real exhaustion open | NOT_STARTED | Approve safe fault fixtures |
| PR-G19 | Page/WAL/schema corruption is preserved/quarantined without unsafe network action | missing evidence | storage/recovery profile | recovery/qualification | NONE selected | FAULTS partial/truncated cases not full acceptance | NOT_STARTED | Approve corruption corpus and restore policy |
| PR-G20 | Exact artifact installs/starts/isolates correctly on every supported entry | missing evidence | MATRIX completed; V1-REL-002 | release qualification | existing install tooling | Windows Docker/NVIDIA/local inference still need applicable exact-RC evidence | NOT_STARTED | Authorize clean-platform qualification |
| PR-G21 | Claimed N/N-1 code/data rollback preserves authority, audit and in-flight-work semantics | missing evidence | upgrade claim; V1-REL-002 | recovery/operations | RECOVERY | No real rollback exercise in this pass | BLOCKED | Define claimed upgrade path and approve exercise |
| PR-G22 | Persisted-schema/protocol compatibility and unknown-major refusal are qualified | scope decision | admitted upgrade/protocol matrix | compatibility owner | NONE selected | Compatibility scope not accepted | NOT_STARTED | Define supported version transitions |
| PR-G23 | Full boot/config validation rejects typo/unknown/unsafe topology states | missing evidence | V1-PP-001 | release/runtime | PROFILE contributes | #472 validates a document; runtime enforcement remains separately required | IN_PROGRESS | Review validator and prove applicable runtime admission |
| PR-G24 | Authorized stop/drain/quarantine/resume/break-glass actions preserve audit and safety | missing evidence | operator policy; AUD1 | operations/security | existing controls contribute | Complete operator exercise missing | NOT_STARTED | Approve operator policy and exact-RC controls |
| PR-G25 | Required actions are auditable; tamper/truncation/tail deletion is detected | missing evidence | audit profile | evidence/security | existing observation chain contributes | Full action-to-audit completeness not accepted | NOT_STARTED | Approve audit scope and independent checks |
| PR-G26 | Independent direct-source seal/manifest/semantic/package/provenance verification passes | missing evidence | V1-PC-001 | evidence reviewer | SEAL | Bounded #447 tooling is not private-source verification | BLOCKED | Select verifier and inspect immutable private bundle |
| PR-G27 | Released execution dependencies/artifacts have reviewed immutable identity, SBOM and acceptable provenance/tamper controls | missing evidence | review; license/artifact identity | supply-chain reviewer | SUPPLY | Pin gate and technical CI PASS; upstream attestation and integration remain | BLOCKED | Review entire stack and accept provenance, not just digest spelling |
| PR-G28 | Complete hash-locked Python and container inputs produce offline/reproducible artifacts bound to selected RC | missing evidence | completed build matrix; trusted resolver authorization | release/build owner | LOCK | Grammar tooling only; no authoritative lock, OS-package policy or offline comparison | BLOCKED | Approve inputs/environment, resolve/build separately, retain and accept evidence |
| PR-G29 | Required CI capabilities are checked and missing capability fails closed without skipped authority | missing evidence | supported test matrix | CI/release owner | OPS/#430 | Retained preflight tooling; no blanket environment-only disposition | IN_PROGRESS | Review capabilities for exact integration/RC lanes |
| PR-G30 | Credential leak/corruption/runaway work/compromise/evidence-breach procedures pass applicable drills | missing evidence | D5; V1-REL-002 | incident/operations lead | OPS/#434 | Plan/validator only; no drill acceptance | BLOCKED | Name lead and authorize separate exact-RC exercises |
| PR-G31 | Any host/region-loss restore/failover claim meets RPO/RTO and uniqueness guarantees | scope decision | D5 loss claims | recovery/operations | NONE selected | No distributed/HA container claim admitted by DOCKER | BLOCKED | Explicitly define applicable restore/loss claims; no implied HA |
| PR-G32 | Receipt type/project/operation/actor/payload binding precedes ACK | reported finding | V1-PC-002 | comms/security owner | NONE selected | FAULTS synthetic observations retained | BLOCKED | Approve applicability then repair/qualify or enforce exclusion |
| PR-G33 | Applicable stale/indeterminate/quarantine states require authorized disposition; age cannot imply success/resend/delete | scope decision | D4; state contract | comms/recovery owner | R5 proposals only | FAULTS separates observation from durable policy | NOT_STARTED | Decide admitted state contract; do not automatically promote all R5 work |

## RELEASE

| ID | Acceptance criterion | Source | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-REL-001 | Review and integrate only selected release changes; qualify resulting main without stale-head transfer | AUD1; CLAIMS; repository ruleset | missing evidence | applicable pre-integration gates, not future exact-RC operational results | release owner | reviewed successor set | No convergence/main mutation by this task | BLOCKED | Authorize guarded integration separately |
| V1-REL-002 | Select immutable RC source/tree/artifact/config/profile/lock identities after convergence and prerequisite builds | CLAIMS; RELEASE; LOCK | missing evidence | V1-REL-001; completed scope/build identities | release owner | candidate manifest/receipt | No selected converged RC | NOT_STARTED | Select identity explicitly; selection alone grants no test/release authority |
| V1-REL-003 | Release receipt keeps historical canary provenance separate from actual RC/final-tag binding | RELEASE | missing evidence | reviewed schema; bind final values after V1-REL-002 | release tooling owner | #428 retained proposal | Proposal is not a completed release receipt | IN_PROGRESS | Review schema before use; confirm final exact identity later |
| V1-REL-004 | Clean installation and recovery on applicable supported entries pass on exact RC artifacts | MATRIX; PR-G20 | missing evidence | V1-REL-002; separate operator authorization | platform qualification | accepted install tooling | No exact-RC evidence | NOT_STARTED | Execute supported Windows/Linux/Docker/browser/provider matrix |
| V1-REL-005 | Approved backup/restore and any claimed rollback preserve data/authority and meet objectives | RECOVERY; PR-G07/G21 | missing evidence | V1-REL-002; D5; separate exercise GO | recovery/operations lead | #461 tooling plus accepted procedure | Validator tests do not authenticate or create observations | NOT_STARTED | Perform and independently accept immutable exercise evidence |
| V1-REL-006 | Approved continuous soak completes on unchanged RC under the declared workload and reset rule | CLAIMS; D5 | missing evidence | applicable exact-RC prerequisite tests; separate soak GO | operations/qualification lead | approved observation procedure | No elapsed soak claimed here | NOT_STARTED | Approve parameters, then measure actual elapsed time |
| V1-REL-007 | Final human GO/NO_GO/ROLLBACK/EVIDENCE_INCOMPLETE disposition binds exact RC and all applicable evidence | CLAIMS; RELEASE | missing evidence | applicable CV-01..17 and linked release gates | release/security/operations/product authority | human decision record | No release authorization | NOT_STARTED | Review and issue genuine final disposition |
| V1-REL-008 | Deploy only approved immutable artifact within the authorized staged/rollback window | RELEASE | missing evidence | V1-REL-007; separate deployment GO | release operator | accepted runbook | No deployment by this task | NOT_STARTED | Authorize and execute separately |
| V1-REL-009 | Final receipt/archive/independent copy and signed release identity bind the qualified artifact without rebuild | RELEASE | missing evidence | V1-REL-007; applicable deployment disposition | release/evidence custodian | accepted release tooling | No tag/release publication | NOT_STARTED | Authorize final publication/archive explicitly |

## R5 / POST-V1

Exact retained planning sources: #410 `49b625b87ba6aea5e62c04af2afe89ebc7ca4266`, #419 `6c417103417b89d6adba1e880f919c20ba98f7dc`, #421 `5d8b9a41671201ac0c0a822ed5d0e5a9124c30ea`. These entries do not become v1 blockers merely because they are incomplete. Promoting an observed invariant violation requires explicit linkage to an applicable v1 gate.

| ID | Acceptance criterion | Source | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-R5-P0 | Review evidence authority and deterministic corpus/phase infrastructure | retained #410/#419/#421 above | optional hardening | post-v1 program review | R5 owner | planning proposals | Retained plans, not current execution | READY_FOR_REVIEW | Review separately from v1 |
| V1-R5-P1 | Qualify versioned authenticated request-bound receipts for admitted scope | retained #410/#419 | optional hardening | V1-R5-P0 | R5 owner | NONE selected | Unexecuted program | NOT_STARTED | Authorize phase independently |
| V1-R5-P2 | Qualify fenced recovery and one durable authority | retained #410/#419; FAULTS | optional hardening | V1-R5-P1 | R5 owner | NONE selected | V1-PC-004 remains independently tracked if applicable | NOT_STARTED | Do not wait for whole R5 program to resolve v1 finding |
| V1-R5-P3 | Qualify crash/corruption/indeterminate/quarantine/stale behavior | retained #410/#419; FAULTS | optional hardening | V1-R5-P2 | R5 owner | NONE selected | Proposed corpus only | NOT_STARTED | Preserve preregistration and first failures |
| V1-R5-P4 | Qualify extended process/topology/lookup/lifecycle/observability | retained #410/#419 | optional hardening | V1-R5-P3 | R5 owner | NONE selected | No phase acceptance | NOT_STARTED | Authorize scope separately |
| V1-R5-P5 | Independently accept immutable phase receipts and final R5 claims | retained #410/#419 | optional hardening | V1-R5-P4 | R5 reviewer | NONE selected | No final phase receipt | NOT_STARTED | Review without granting v1 authority |

## RESEARCH

| ID | Acceptance criterion | Source | Classification | Dependencies | Owner | Implementation | Test/evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|---|---|
| V1-RES-001 | Published chronology marks old derived 44/44 claims superseded by direct-manifest evidence; no invented corrected seal | #411 1e2592bfc81dfe94d0f39332ebd451862680cab4; #415 3da0d8ec45adf8934b88906462706617aa22831f | missing evidence | publication/source verification | research/evidence owner | original docs, unchanged | Historical publication reconciliation, not private verification | BLOCKED | Review before that research publication; not an automatic extra v1 experiment |
| V1-RES-002 | Maintain claim/evidence alternatives, ablations and replication without unsupported novelty claims | #424 352029e88573023cbe81a7288601189bd93311c7 | hypothesis | research review | research owner | #424 | Retained research matrix | READY_FOR_REVIEW | Review separately |
| V1-RES-003 | Reproducibility registry distinguishes retrospective observations from preregistration | #420 b36b15f1b161ff8d7a913ca47f8a3bea3fab660c | optional hardening | research review | research owner | #420 | Retained registry | READY_FOR_REVIEW | Preserve frozen protocols |
| V1-RES-004 | Environment drift and unavailable capabilities are recorded before interpreting results | #425 052065c76955f772bb2ac6c49fe67fcc66ecfc20 | reported finding | exact environment evidence | research/CI owner | OPS preflight contributes | Historical count/capability discrepancies retained | READY_FOR_REVIEW | Separate observer/test-environment failure from target failure |

#450/#451/#459/#460/#470/#471 and other research/UX/automation work do not enter the v1 critical path unless a separately evidenced applicable blocker is linked. No research branch is rebased or bulk-integrated here.

## Current disposition

PROFILE and SUPPLY are actually non-draft and technically qualified on their stated heads, but unmerged and not human-reviewed. This consolidating master revision needs its own exact-head CI and human review; predecessor CI does not qualify it. There is no selected converged release tree, completed current F6 bundle, current canary acceptance, private direct-source verification, authoritative offline reproducible release build, exact-RC operational evidence or final release authorization established by this task.

Only the master read-model and review-routing metadata changed in this pass. No frozen source/evidence, helper, live service, credentials, ownership pins, assertions, required test, deployment topology, schedule, main, canary, physical F6, provider workload, recovery exercise, elapsed soak, tag, release, approval or human attestation was changed or executed.
