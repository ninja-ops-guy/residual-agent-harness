# Current-State Gap Audit — RESIDUAL vs MS-00…08 / G0…G7 target architecture

**Audit observation, not a qualification claim.** Audited head: `main@3cff6bcd52e352a6ba048c958949a7bbb2a039eb` (verified via GitHub API, 2026-09-18). Re-audit of the Wave-A A4 audit performed at `main@699e2869e294fe157b4bfd73a272057683a2f7e0` (7 PASS / 20 PARTIAL / 11 ABSENT / 5 UNKNOWN).

Repo prose (`docs/CURRENT_STATUS.md`) is bound to `main@4608afab…` (#205). Any evidence cited from prose is bound to that older revision, not to the audited head `3cff6bcd`; per program rules such evidence is marked UNKNOWN where a current-revision binding is required.

## Verdict legend

PASS = implementation + test + retained evidence bound to the audited head (no prose-only PASS). PARTIAL = some elements present. ABSENT = nothing found. UNKNOWN = evidence exists but is stale/ambiguous/unverifiable at the audited head. BLOCKED = progress prevented by an identified dependency.

## Main drift since prior audit head `699e2869`

Merged between `699e2869` and `3cff6bcd` (verified via commit list):

| PR | Merge SHA | Audit impact |
|---|---|---|
| #200 setup safe defaults | `fc1eb8b1` | P0-5 adjacent: local/persistent setup defaults; blank-environment install still not established |
| #205 provider-channel recovery | `4608afab` | P0-9 adjacent: reload/remount channel recovery PASS on main; live-provider success still UNKNOWN |
| #216 current-state refresh | `96bcf55b` | docs only |
| #218 station M6 repair-loop lessons | `d665b188` | station lane; no architecture-row change |
| #201 frontend guided proof | `260b5f9e` | P0-9 adjacent: embedded provider setup/proof |
| #233 station repair failure retention | `60d0c5a8` | retains first-failure tail; no verdict change |
| #248 provider load lifecycle | `de7d9774` | P0-9 adjacent: bounded provider load lifecycle qualified on current main |
| #197 PR Agent advisory hardening | `3cff6bcd` | P2-2 adjacent: CI review hardened as advisory |

Open relevant PRs at audit time (not accepted main): #152 Qualification v1 framework, #118 fencing/cancellation runtime closure, #115 blank-VM + soak plan, #93/#167 orchestration-tax observability, #162 backpressure spec, #214 budget-ordering repair candidate, #275 maintainer-approval head-status fix, #276 Pages per-SHA qualification gate.

## P0 — Release blockers

| # | Requirement | Implementation | Tests | Evidence | Verdict | Future owner |
|---|---|---|---|---|---|---|
| P0-1 | Frozen RC / stabilization lane | `docs/release/STABILIZATION_2026-09-17.md` (lane + exit criteria; all 12 exit checkboxes still unchecked at head) | — | the doc itself | PARTIAL — unchanged | Release eng |
| P0-2 | Exact-head CI | 25 workflows in `.github/workflows/` | self-executing | `docs/CURRENT_STATUS.md` records exact-head PASS at `4608afab`, not at audited head `3cff6bcd` | UNKNOWN at audited head | Release eng / CI |
| P0-3 | Capable-runner M4 qualification | `residual/factory/m4_sandbox.py`, `residual/factory/m4_qualification_prereq.py`, `scripts/m4_trust_evidence.py`, `.github/workflows/m4-qualification-prereq.yml` | `tests/test_factory_m4_qualification_prereq.py`, `test_factory_m4_sandbox.py`, `test_factory_m4_safety.py` | `evidence/m4-qualification-prereq/`, `runs/m4-trust/`; CURRENT_STATUS: "universal/capable-runner M4 qualification: not established" | PARTIAL — unchanged | Factory/M4 + CI runners |
| P0-4 | Artifact freeze (wheel bound to commit/tree) | `verifier/v3/qualify_clean_install.py`; `docs/status/CLEAN_INSTALL_QUALIFICATION.md` | `tests/test_clean_install_qualification.py` | clean-install-qualification.yml reports | PARTIAL — unchanged | Release eng |
| P0-5 | Blank-VM install | venv-level clean install only; #200 hardened setup defaults (persistent XDG paths, opt-in shell macro) | `tests/test_clean_install_qualification.py` | clean-install CI reports (venv scope); CURRENT_STATUS: "true blank-environment installation: UNKNOWN / not established" | PARTIAL (venv) / ABSENT (blank-VM); in-flight PR #115 | Release eng |
| P0-6 | Host-loss / recovery evidence | `residual/hadr/restore.py`, `residual/hadr/failover.py`; runbook `docs/enterprise/governance/runbooks/station-failure.md` | hadr tests | no retained real host-loss evidence | PARTIAL (mechanism) / UNKNOWN (evidence) — unchanged | HADR |
| P0-7 | 24h/72h wall-clock soak | `residual/soak/harness.py` (deterministic simulator) | `tests/test_soak.py`, `test_soak_report.py`, `test_soak_state.py` | none elapsed; CURRENT_STATUS: "production long-run reliability: not established" | ABSENT for wall-clock claim; in-flight PR #115 | Soak/infra |
| P0-8 | Real-provider E2E | `residual/providers.py` client + protocol validation | `tests/test_providers.py`, `test_connector_conformance.py` | historical live Puter mission `m-b98fe1b9…` FAIL/BLOCKED retained; CURRENT_STATUS: live-provider success "UNKNOWN / not established" post-#205 | UNKNOWN/ABSENT — unchanged | Provider integration |
| P0-9 | Provider helper production verification | #189 (COOP/COEP bypass) + #201 (embedded provider setup) + #205 (channel recovery) + #248 (load lifecycle) all merged | pages/browser proof tests | CURRENT_STATUS: "retained manual production SDK/sign-in success on exact current main: UNKNOWN / not established" | PARTIAL (impl merged) / UNKNOWN (production verification) — narrowed but not closed | WebVM/provider |
| P0-10 | iPhone/Safari fallback | `demo/vm/ios_webkit_preflight_smoke.py`; `.github/workflows/ios-webkit-preflight.yml` | `tests/test_webvm_ios_preflight.py` | fallback-contract CI; issues #120/#126 open | PASS (fallback contract scope) / UNKNOWN (heavyweight path) — unchanged | WebVM |
| P0-11 | Repeated WebVM campaign | `webvm-runtime-*.yml` (9 workflows); `docs/repeated-live-evidence-design.md` | `tests/test_webvm_*.py` | no retained repeated-campaign result set | PARTIAL — unchanged | WebVM |

## P1 — Production-control proof

| # | Requirement | Implementation | Tests | Evidence | Verdict | Future owner |
|---|---|---|---|---|---|---|
| P1-1 | HITL approver identity binding | `residual/hitl/gateway.py` (host-supplied `authenticate`; fail-closed when None) | `tests/test_tracks_2_8.py` | — | PARTIAL — unchanged | Security/HITL |
| P1-2 | Approval replay prevention | `hitl/gateway.py` atomic single-use consume (`BEGIN IMMEDIATE`) | `tests/test_tracks_2_8.py` | CI | PASS (mechanism+test) — unchanged | Security/HITL |
| P1-3 | Restart terminal-state preservation | `residual/factory/runtime_journal.py` — hash-chained append-only events (immutability triggers), UNIQUE constraints, refuses corrupt persisted chain on restart (`self.observations()` in `__init__`), bounded writer-admission retry (R1 repair merged pre-audit) | `tests/test_lifecycle_glue_resume.py`, `test_release_stabilization_runtime_journal.py` | R1 first-failure retained in STABILIZATION doc; bounded-retry repair present at head; no retained exact-head rerun of the failing 3.11 scenario | PARTIAL — R1 repair merged, requalification evidence outstanding | Control plane |
| P1-4 | No duplicate accepted external action | `residual/control_plane/transactions.py` (in-memory saga, AMBIGUOUS/RECONCILING); `runtime_journal.claim()` rejects second active attempt per (plan_hash, task_id) | `tests/test_control_plane.py`, `test_gateway_bypass.py` | —; **new retained FAIL evidence**: #207 STRESS-B1 and #212 missing-usage case show accepted integration/release before accounting aborted (`usage_unknown_or_invalid`); #214 repair is draft/BLOCKED | PARTIAL with retained negative evidence — scope limited to Factory attempts; ordering defect open | Control plane |
| P1-5 | Provider-secret boundary | `residual/providers.py` (safe error codes); `residual/quarantine.py` | `tests/test_providers.py`, `test_loop_layer.py` | — | PARTIAL — unchanged | Security |
| P1-6 | Secret-leakage scan | none found in `.github/workflows/` (25 workflows checked) or scripts | — | — | ABSENT — unchanged | Security/CI |
| P1-7 | Liveness/readiness/mission-success endpoint separation | runbook mentions `/healthz` only | — | — | ABSENT — unchanged | Station/ops |
| P1-8 | Bounded queues / backpressure | none; spec-only PR #162 open | — | — | ABSENT — unchanged | Orchestration |
| P1-9 | Graceful shutdown handoff | `residual/hadr/failover.py`; no SIGTERM/drain in station | — | — | PARTIAL (failover design) / ABSENT (drain) — unchanged | HADR/Station |
| P1-10 | Schema migration strategy | `CREATE TABLE IF NOT EXISTS` only (`residual/station/store.py`, `runtime_journal.py`) | — | — | ABSENT — unchanged | Storage |
| P1-11 | Disaster/restart matrix | `scripts/factory_termination_matrix.py`; `swarm3-termination-matrix.yml` | `tests/test_factory_termination_matrix.py`, `test_factory_termination_provenance.py` | CI runs | PARTIAL — unchanged | Factory/SRE |
| P1-12 | HA limitation docs | `docs/enterprise/ENTERPRISE_SPECS.md`, runbooks (RTO 15min/RPO 5min) | — | docs | PARTIAL — unchanged | Docs/SRE |
| P1-13 | Operator runbook | `docs/enterprise/governance/runbooks/` (5 runbooks) | — | the docs | PASS (existence); operational validation UNKNOWN | Docs/SRE |
| P1-14 | Integrated recovery suite | `residual/hadr/restore.py`, `residual/workbench/host_recovery.py` | hadr/webvm recovery tests | — | PARTIAL — unchanged | HADR |

## P1 — Observability / SLO

| # | Requirement | Implementation | Tests | Evidence | Verdict | Future owner |
|---|---|---|---|---|---|---|
| P1-15 | SLO definitions | `residual/observability/slo.py` DEFAULT_SLOS | `tests/test_observability_hardening.py` | CI | PASS (definitions+tests); production compliance UNKNOWN | Observability |
| P1-16 | Latency percentiles | histogram `MetricsRegistry` in `observability/metrics.py` | `tests/test_observability_hardening.py` | — | PARTIAL — unchanged | Observability |
| P1-17 | Orchestration overhead vs model latency | none; in-flight PRs #93/#167 | — | — | ABSENT — unchanged | Observability |
| P1-18 | Cost / tokens | `residual/providers.py` token-usage validation + pricing fields | `tests/test_providers.py` | —; #212 retained FAIL shows usage can be unknown while integration proceeds | PARTIAL with retained negative evidence | Observability |
| P1-19 | Bounded-cardinality metrics | `observability/completeness.py` + exporter | `tests/test_observability_hardening.py` | — | PARTIAL/UNKNOWN — unchanged | Observability |
| P1-20 | Telemetry-failure isolation from verifier semantics | no mechanism found | — | — | UNKNOWN (likely ABSENT) — unchanged | Observability/Verifier |
| P1-21 | Sanitized diagnostic exports | webvm diagnostics tests; `observation_layer/` | `tests/test_webvm_diagnostics.py` | retained diagnostics in `docs/research.md` | PARTIAL — unchanged | WebVM/Observability |
| P1-22 | Failure-bundle sufficiency | per-run `runs/`, `evidence/` dirs | — | e.g. `runs/m4-trust/`, `evidence/m4-qualification-prereq/` | UNKNOWN — no sufficiency standard | Observability |

## P2 — Release engineering + governance

| # | Requirement | Implementation | Tests | Evidence | Verdict | Future owner |
|---|---|---|---|---|---|---|
| P2-1 | Factory ownership gate | `verifier/v3/check_factory_ownership.py` + baseline; `factory-ownership.yml` | `tests/test_factory_ownership_gate.py` | `docs/status/FACTORY_OWNERSHIP_GATE.md` | PASS — unchanged | Release eng |
| P2-2 | Maintainer approval gate | `scripts/check_maintainer_approval.py`; `maintainer-approval.yml` | `tests/test_maintainer_approval_gate.py` | per-head results; known gap: status not published on exact PR head (open fix PR #275) | PASS (mechanism) with known status-publication gap | Governance |
| P2-3 | Traceability manifest | `implementation-status.yaml` + `scripts/status_check.py`; `docs/status/IMPLEMENTATION_STATUS.md` | `tests/test_traceability.py` | the manifest | PASS — unchanged | Governance |
| P2-4 | Verifier qualification runs | `verifier/runs/` retained logs | — | logs bound to older revisions | UNKNOWN at audited head — unchanged | Verifier |

## MS-00…08 / G0…G7 target-architecture rows (new)

Scope note: `residual/factory/runtime_journal.py` is a Factory-scoped durable local journal, not the shared authoritative control store; several rows are PARTIAL only at that narrower scope and ABSENT at the target scope.

| # | Requirement | Implementation | Tests | Evidence | Verdict | Future owner |
|---|---|---|---|---|---|---|
| MS-A | Shared authoritative control store | none; closest: Factory-scoped `residual/factory/runtime_journal.py` (SQLite WAL, FULL sync) + in-memory `residual/control_plane/transactions.py` | — | — | ABSENT (target scope) | Control plane |
| MS-B | Dedicated MS-08 writer service | none; no "writer service" occurrences (code search) | — | — | ABSENT | Control plane |
| MS-C | Per-lane observation shards | shared schema `residual/observation_layer/` (hash-chained `Observation`, `SCHEMA_VERSION`, `verify_chain`); per-domain evidence dirs (`evidence/dsm\|obs\|otx\|vq\|runtime\|eval`) | observation tests | dirs retained | PARTIAL — schema and per-domain evidence exist; not per-lane shards bound to a control store | Control plane/Observability |
| MS-D | Local emergency journals | `runtime_journal.py` module docstring: "A FULL-synchronous SQLite transaction commits each event before acknowledgement"; append-only triggers; Factory scope only | `tests/test_release_stabilization_runtime_journal.py` | — | PARTIAL (Factory scope) / ABSENT (per-lane emergency journals) | Control plane |
| MS-E | Storage-enforced exactly-one-terminal (CAS + uniqueness) | Factory scope: UNIQUE constraints on attempt/worker/lease/workspace; single-active-attempt check in `claim()`; terminal-transition guard in `finish()`; no compare-and-swap ledger across lanes; control-plane saga is in-memory | `tests/test_lifecycle_glue_resume.py` | — | PARTIAL (Factory attempts) / ABSENT (control-plane terminal states) | Control plane |
| MS-F | Commit-before-ack | Factory journal commits before acknowledgement (docstring above); HITL gateway atomic consume; no writer-service ack protocol | `tests/test_tracks_2_8.py` | — | PARTIAL (component scope) / ABSENT (service scope) | Control plane |
| MS-G | Fencing | Factory lease generation monotonicity ("lease generation must increase across attempts" in `claim()`); tri-state lease reads (`LeaseRead`); browser poison-record fences in `workbench/browser_worker.py`; no control-plane fencing tokens; fencing/cancellation closure in open PR #118 | `tests/test_webvm_poison_restart.py` (browser scope) | — | PARTIAL (Factory/browser scope) / ABSENT (control-plane fencing); in-flight PR #118 | Control plane |
| MS-H | Provider resolver contract | `residual/providers.py` is a client, not a resolver contract | — | — | ABSENT — unchanged | Provider integration |
| MS-I | D0–D4 determinism classes | no occurrences of D0–D4/determinism-class in code or specs (code search) | — | — | ABSENT — unchanged | Architecture |
| MS-J | G0–G7 gate evidence index | no occurrences; Qualification v1 framework in open PR #152 (review-accepted, not merged at audit time) | — | — | ABSENT; in-flight PR #152 | Release eng / verifier |
| MS-K | Startup reconciliation | journal refuses corrupt persisted chain on restart (`runtime_journal.__init__` → `observations()` → `verify_chain`); saga RECONCILING states; no reconciliation pass over a durable ledger at startup | — | — | PARTIAL — unchanged | Control plane |

## Summary counts (audited head `3cff6bcd`; 48 rows: 37 carried P0/P1/P2 rows + 11 MS rows; prior WA-1…WA-6 rows are subsumed into MS-A…MS-K)

| Verdict | Count | Change vs prior audit |
|---|---|---|
| PASS | 7 | 0 |
| PARTIAL | 25 | +5 (new MS rows MS-C/MS-D/MS-E/MS-F/MS-G/MS-K are PARTIAL; no P0/P1/P2 row upgraded to PASS) |
| ABSENT | 11 | 0 net (MS-A/MS-B/MS-H/MS-I/MS-J ABSENT added; WA ABSENT rows subsumed) |
| UNKNOWN | 5 | 0 |
| BLOCKED | 0 as verdict; 1 flagged dependency (P1-4 ordering repair #214 draft/BLOCKED; verdict remains PARTIAL with retained FAIL) | new note |

No prior PARTIAL/ABSENT/UNKNOWN verdict upgraded to PASS: the eight merges since `699e2869` (#200/#201/#205/#216/#218/#233/#248/#197) narrowed P0-5/P0-9/P2-2 scope and retained new failure evidence (P1-4, P1-18), but none produced retained evidence bound to `3cff6bcd` that closes a row.

## Dependency-ordered backlog (updated)

Ordering principle unchanged: control-plane truth before recovery/restart proofs; evidence manifest before gates; gates before RC freeze.

**Tier 0 — Foundations**
1. MS-A/MS-E control-plane ledger (CAS + storage uniqueness, exactly-one-terminal). Unblocks MS-B, MS-K, P1-3/P1-4 rewiring, P1-14.
2. MS-I D0–D4 determinism classes. Unblocks soak-claim classification (P0-7), manifest schema, MS-J gates.
3. MS-J prerequisite: machine-readable evidence manifest (extends `implementation-status.yaml`). In-flight framework: PR #152 (open; refresh before use per CURRENT_STATUS blocker #10).

**Tier 1 — Writer + reconciliation + provider contract**
4. MS-B/MS-F writer service (commit-before-ack) + MS-G fencing tokens. Depends on MS-A. In-flight partial: PR #118.
5. MS-K startup reconciliation over the ledger. Depends on MS-A/MS-B. Unblocks P1-14, P0-6 evidence generation.
6. MS-H provider resolver contract. Blocks P0-8 and P1-5 boundary proof.

**Tier 2 — Production-control closure**
7. P1-3/P1-4 rewiring onto the ledger; requalify the #207/#212 accounting-before-authority FAIL cells (repair candidate #214 currently draft/BLOCKED — **retain the failures; do not weaken tests to green**).
8. P1-10 schema migration strategy (parallel with MS-A).
9. P1-7 health separation + P1-8 backpressure (spec #162) + P1-9 graceful drain.
10. P1-1/P1-5/P1-6 security lane (P1-6 secret scan is cheap/standalone).
11. P1-14 integrated recovery suite against the reconciled ledger; feeds P0-6.

**Tier 3 — Observability/SLO closure**
12. P1-16/P1-17 (PR #93)/P1-18/P1-19 metrics completion.
13. P1-20 telemetry-failure isolation design (blocks P1-22).
14. P1-21/P1-22 sanitized exports + failure-bundle sufficiency standard (needs Tier 0 manifest).

**Tier 4 — Evidence generation at exact head**
15. MS-J G0–G7 gate certification (manifest + PR #152 framework).
16. P0-3 capable-runner M4 qualification run (`blocked_capabilities: []` for `linux-userns-isolated-v1`).
17. P0-5 blank-VM install (PR #115), P0-6 host-loss runs, P0-7 elapsed soak (real executor behind `SoakHarness._execute_task`), P0-8 real-provider E2E (needs MS-H), P0-9 production helper verification, P0-10 physical iPhone qualification, P0-11 repeated WebVM campaign.
18. P0-1 frozen RC + P0-2 exact-head CI + maintainer attestation. Depends on all Tier 4.

**Critical path:** MS-A ledger → MS-B writer/fencing → MS-K reconciliation → P1-14 recovery suite → P0-6/P0-7 evidence → MS-J gate certification → P0-1 RC freeze.

**Parallel lanes:** security (10), observability (12–14), device/provider evidence (P0-5, P0-9, P0-10, P0-11 — not gated on the ledger).
