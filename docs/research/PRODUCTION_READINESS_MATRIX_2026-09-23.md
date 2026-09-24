# Production-readiness gap audit — 2026-09-23

Static/read-only audit of `main` at `91d32fd8b713c68c1cd2e473013c9e1c33b93572`.
R4.1 candidate `8701367db6d3202f24b3eb9f4696b0cadf657985` was referenced and not modified.
This is qualification planning, not a deployment authorization.

Classifications: `P0_PRE_CANARY` means a credible risk to the currently proposed
live canary boundary; `P1_PRE_PRODUCTION` means required before an Internet-facing,
multi-user, or durable production service; `P2_POST_V1` is hardening; `RESEARCH`
needs empirical work before a product requirement is asserted.

## Matrix

| Area | Evidence / gap | Class | Proposed qualification gate |
|---|---|---|---|
| authentication | Bearer/session tokens use constant-time comparison, but unauthenticated `/api/bootstrap` returns the session token to an allowed Host; safe only under the documented loopback trust boundary | P1_PRE_PRODUCTION | PR-G01 prove bootstrap is unreachable to untrusted clients in every supported bind/proxy topology |
| authorization | Session token is station-wide; worker token gates all enabled remote-worker endpoints, with project IDs selected in requests | P1_PRE_PRODUCTION | PR-G02 principal/role/project matrix with cross-project confused-deputy negatives |
| credential lifecycle | Worker token rotation exists; provider keys are stored in SQLite settings; no expiry, external KMS, encryption-at-rest, or complete revocation evidence | P1_PRE_PRODUCTION | PR-G03 rotate/revoke/expire every credential during active and queued work |
| secret exposure | Public settings redact key values; credentials remain in the same database/OS account trust domain | P1_PRE_PRODUCTION | PR-G04 taint corpus across APIs, logs, errors, exports, backups, and process environment |
| TLS assumptions | Remote worker client requires HTTPS except loopback; Station itself is plain HTTP and depends on external termination when non-loopback | P1_PRE_PRODUCTION | PR-G05 topology matrix binds trusted proxy headers, certificate validation, redirect refusal, and downgrade rejection |
| persistence | SQLite WAL and explicit transactions are present; durability mode and filesystem assumptions are not declared | P1_PRE_PRODUCTION | PR-G06 power-loss/WAL/fsync matrix on every supported filesystem |
| backup/recovery | No versioned, exercised Station backup/restore contract located | P1_PRE_PRODUCTION | PR-G07 encrypted backup, restore, point-in-time/RPO/RTO, and integrity rehearsal |
| crash consistency | Event/task transactions exist; Shared Comms ACK and broader multi-artifact operations need crash-point enumeration | P1_PRE_PRODUCTION | PR-G08 deterministic crash at every state/external-effect boundary |
| concurrency | In-process `RLock` and SQLite `BEGIN IMMEDIATE` serialize Store transactions; no multi-process ownership contract | P1_PRE_PRODUCTION | PR-G09 process/host contention and explicit unsupported-topology fail-closed test |
| observability | Observation chain/export exists; routine HTTP access logging is deliberately suppressed | P1_PRE_PRODUCTION | PR-G10 required security/operation event schema, loss injection, redaction, and reconciliation |
| logging | Ollama stdout/stderr append to one file; rotation, retention, disk budget, and correlated request audit are not evident | P1_PRE_PRODUCTION | PR-G11 bounded rotation/retention plus disk-full and hostile-content tests |
| metrics | Project metrics and observation summaries exist; service SLO/exporter contract is not evident | P1_PRE_PRODUCTION | PR-G12 recompute low-cardinality service metrics from authoritative journal |
| tracing | Trace-oriented observations exist; no end-to-end network/job/worker propagation qualification located | P2_POST_V1 | PR-G13 trace continuity, sampling, loss, clock-skew, and secret-leak corpus |
| resource limits | Request bodies and worker responses are capped; model/install/job/log/disk/process-wide budgets are incomplete | P1_PRE_PRODUCTION | PR-G14 CPU/memory/fd/thread/process/disk/network exhaustion matrix |
| timeout bounds | Several network/subprocess timeouts are explicit; worker POST is 600s and retry/time budgets are not uniformly compositional | P1_PRE_PRODUCTION | PR-G15 enumerate every blocking operation and prove a global upper bound/cancellation path |
| retry bounds | Some transport retry is one-shot and R4.1 recovery fails closed on lookup outage; system-wide retry budgets/jitter are not declared | P1_PRE_PRODUCTION | PR-G16 fault matrix proves bounded attempts, backoff, jitter, and no retry amplification |
| rate limiting | No Station HTTP authentication or operation rate limiter located | P1_PRE_PRODUCTION | PR-G17 per-principal/IP/operation limits with concurrency, bypass, and recovery tests |
| disk exhaustion | Diagnostics expose free space; writes do not share a qualified reserve/fail-closed policy | P1_PRE_PRODUCTION | PR-G18 ENOSPC/inode/quota/read-only injection at DB, artifacts, logs, and evidence |
| database corruption | Hash-chained events detect semantic tampering; SQLite page/WAL corruption recovery/quarantine is not qualified | P1_PRE_PRODUCTION | PR-G19 corruption corpus, forensic preservation, bounded quarantine, restore |
| deployment | Local CLI/default loopback is clear; no supported production topology manifest or immutable deployment artifact contract located | P1_PRE_PRODUCTION | PR-G20 reproduce install/start/health/isolation from signed artifact on clean host |
| rollback | R4 demonstrated candidate-only rollback; database/schema and deployed-version rollback compatibility remain broader questions | P1_PRE_PRODUCTION | PR-G21 N/N-1 code+data rollback with in-flight work and preserved audit chain |
| upgrade compatibility | Persisted rows/events have partial schema versions; explicit compatibility negotiation/migrations are incomplete | P1_PRE_PRODUCTION | PR-G22 old/new rolling matrix and unknown-major fail-closed behavior |
| configuration validation | Route and numeric settings are strongly bounded; cross-field deployment/security invariants remain implicit | P1_PRE_PRODUCTION | PR-G23 boot-time complete config validation with typo/unknown/unsafe topology corpus |
| operator controls | Pause, access disable/rotate, task review/integrate exist; break-glass, dual control, and safe-mode runbooks are not evident | P1_PRE_PRODUCTION | PR-G24 authenticated/operator-audited stop, drain, quarantine, resume, break-glass tests |
| auditability | Hash-chained events and evidence receipts are strengths; access/security/operator actions are not shown to form one complete audit contract | P1_PRE_PRODUCTION | PR-G25 action-to-audit completeness and tamper/truncation/tail-deletion detection |
| evidence integrity | Fail-closed R4 gates and independent Seal v2 verification are strong; PR #415 shows derived cardinality previously became authority | P0_PRE_CANARY | PR-G26 freeze independent verifier and recompute all seal claims directly before any canary authorization |
| supply-chain controls | Qualification includes provenance work; many GitHub actions use floating major tags rather than immutable SHAs | P1_PRE_PRODUCTION | PR-G27 action/dependency/artifact SBOM, signature, provenance, and tamper verification |
| dependency pinning | Qualification extras are exact-pinned; runtime dependency range and build requirements are not lockfile/hash pinned | P1_PRE_PRODUCTION | PR-G28 clean offline/reproducible build from hash-locked dependency set |
| CI/CD | Extensive workflows and explicit permissions exist; runner capability variance already makes broad results non-portable | P1_PRE_PRODUCTION | PR-G29 capability-preflight every lane and fail closed on missing mandatory capability |
| incident response | No single tested Station incident-response runbook/rehearsal located | P1_PRE_PRODUCTION | PR-G30 credential leak, corruption, runaway job, compromise, and evidence-breach tabletop+drill |
| disaster recovery | No qualified multi-host restore/failover authority and split-brain prevention contract located | P1_PRE_PRODUCTION | PR-G31 regional/host loss restore with RPO/RTO, fencing, and uniqueness preservation |
| receipt semantics | Frozen candidate probe accepts wrong-project/wrong-operation/non-object receipts into local `ACKED` when its transport is synthetically subverted | P0_PRE_CANARY | PR-G32 require exact client-side receipt binding before ACK; independent scope review decides canary disposition |
| stale/indeterminate state | Current outbox has `PENDING`/`ACKED`; stale is computed by age and lookup outage remains `PENDING` | P1_PRE_PRODUCTION | PR-G33 durable state graph, operator disposition, and age/clock anomaly tests |

## Immediate review points

1. `P0_PRE_CANARY` PR-G26 is process/governance: Seal v2 currently verifies, but
   the frozen verifier and direct-source recomputation must remain prerequisites.
2. `P0_PRE_CANARY` PR-G32 is a newly reproduced candidate-scope question, labeled
   `BLOCKING_CANDIDATE_FINDING`. The probe used a synthetic authenticated-channel
   substitute; reviewers must decide whether the canary threat model requires
   client-side receipt binding now or explicitly defers it to R5. No automatic
   repair or requalification was performed.
3. A default loopback-only Station is not equivalent to an Internet-facing
   production service. Most P1 findings become urgent when broad binding,
   reverse proxying, multi-user access, or durable service guarantees are claimed.

Evidence sources: current source/config/workflows, PRs #410/#415, frozen R4.1
runtime evidence, and disposable frozen-candidate probes. Tests performed:
static inspection and offline synthetic fault probes. Blockers: no production
topology/SLO/RPO/RTO authority was supplied. Research: distributed lookup,
downstream at-most-once boundaries, and filesystem crash semantics require
controlled study. Canary execution status: **NOT EXECUTED**. Production systems
were not modified.
