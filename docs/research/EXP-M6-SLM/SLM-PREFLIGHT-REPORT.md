# SLM-00 PREFLIGHT REPORT — Retained AX-21 / Swarm Evidence → SLM Corpus Feasibility

Lane: SLM-PF (Preflight)
Date: 2026-09-20
Base branch: `research/exp-m6-slm-00` @ commit `3661319eee03963943a6df88db61243254134983`
Schema under test: `docs/research/EXP-M6-SLM/observation.schema.json` (blob `6e549b05e0fab3684d6ec7173985aa734e55ffca`)
Protocol: `docs/research/EXP-M6-SLM/SLM-00-PROTOCOL.md` (blob `a3ea085a406fbf1e23186e2a725742072897df02`)

**VERDICT: CONDITIONAL-GO** — Structured swarm evidence (OTX/OBS/DSM/VQ/RUNTIME/M4 lanes) is hash-anchored, reproducible, and mechanically transformable with a documented mapping and strictly null/unknown handling of absent fields. However, (a) zero records carry wall-clock timestamps, so strict schema validity requires a schema erratum (nullable/optional `timestamp`) — inventing timestamps is prohibited; and (b) organic AX-21 dogfooding evidence is narrative-only and is NOT corpus-eligible at event level. Scope must be reduced accordingly.

---

## 1. Evidence inventory (all paths @ `research/exp-m6-slm-00` = `3661319e...` unless noted)

| # | Source | Path | Blob SHA | Records sampled | Class |
|---|--------|------|----------|-----------------|-------|
| 1 | OTX-003 orchestration-tax observations | `evidence/otx/observations.jsonl` | `9d24ececfe5e52a3732d6f5cc6c571d8af125ca2` | 24/24 JSONL records (otx-000001..otx-000024) | replay/benchmark |
| 2 | OBS-006 observability fixture | `evidence/obs/obs006-evidence.json` | `4f140a2266df0c6b6f66f6a88a519b52a1c58182` | 22/22 raw observations | synthetic fixture |
| 3 | DSM-004 distributed-state journals | `evidence/dsm/dsm-004-evidence.json` | `20c8e7e4d8ad99dc0b5b0b73085388ab14477620` | 12 journal files, ~60 hash-chained events; 6-schedule fault matrix; 3 recovery scenarios | replay (fault-injection) |
| 4 | RUNTIME-005 engine evidence | `evidence/runtime/runtime005_evidence.json` | `76358dd1a1054e596a5e04c167dd84792e809dd0` | 2 conformance engines × 12 checks; 5 fault scenarios | synthetic/replay |
| 5 | VQ-002 verifier-quality outcomes | `evidence/vq/outcomes-{adequate,degraded}.part{0,1,2}.jsonl` | part0 adequate: `e79f2946fd30cc11994a2015f35668fb4e9ab808` | 50/50 lines read from part0; ~260 records total across 6 parts (by size/line-length estimate) | benchmark (frozen workload) |
| 6 | EVAL fixture-study aggregates | `evidence/eval/fixture-study.csv` | `2ef6fe922d7127318f2b270688fc25164854117f` | 6/6 rows (R0–R5) | aggregate — NOT observation-level |
| 7 | M4 trust-boundary run | `runs/m4-trust/m4-trust-report.json` | `5b7d13753ec6005fa00292f798b768944054645a` | 6 git-evidence scenarios, 7 adversarial trials, 6 suites | replay/qualification |
| 8 | Sandbox-timing determinism | `runs/sandbox-timing/determinism-report.json` (+2 repeat reports) | `75d4ed06b04676dba2fe3ecd67e72131c43616ae` | n10 determinism proof, 2×20 repeat runs | replay/qualification |
| 9 | **AX-21 federated dogfood log** | `docs/swarm/ax21-federated-dogfood-log.md` @ branch `research/ax21-dogfood-log` (commit `c82924ccce18808aa7eca39a439f4d2cee8fbf96`) | `2a5983422959236f9edae5a17015e184f4e258db` | full document (11,894 bytes) | **ax21 organic — narrative only** |

Note: `search_code` for `AX-21`/`ax21`/`dogfood` returns 0 hits on the default branch; the only AX-21 artifact found anywhere in the repo is source #9 on its unmerged branch. No AX-21 evidence is present on `research/exp-m6-slm-00` itself.

## 2. Schema-conversion sampling results

Required top-level fields per schema: `schema_version, observation_id, timestamp, provenance, state, proposed_decision, actual_decision, outcome, verification, cost, authority` (`additionalProperties: false`).

### 2.1 OTX (24 records) — highest-quality candidate
Present: `observation_id`, `sequence`, `inputs` (→`state`), `candidates`+`selected_topology`+`selection_reason` (→`proposed_decision`/`actual_decision`), `result` (→`outcome`), `model_snapshot.sha256` (→`provenance.artifact_digests`), `comparison.within_1_std`, timing breakdown (→`cost.latency_ms` via deterministic ms conversion).
Missing/unknown (per-record, 24/24): `schema_version` const (settable deterministically), `timestamp` (**absent — must stay unknown; schema currently forbids null**), `provenance.source_class` (settable to `replay`/`benchmark` — these are model-driven topology-selection replays), `mission_id`/`incident_id`/`generation` (absent → null), `verification.status` (mappable: `result.success && quality_score==1.0` → `verified_success` would be an **interpretation**, not a recorded verification; honest mapping is `unknown` or `provisional`), `authority` (absent → must default to empty requested/granted, violation=false — **this is an assumption to document, not a recorded fact**), `contamination_group` (recoverable, see §4), `cost.inference_usd`/`energy_wh`/`operator_active_seconds`/`frontier_calls` (absent → null).
Strict validity without invented fields: **0/24** (timestamp). With schema erratum allowing null timestamp: **24/24** convertible deterministically.

### 2.2 OBS-006 (22 raw observations)
Self-reported completeness: 19/22 complete, 3/22 with missing fields (execution ×2, integration ×1, verification ×1 — counts corroborated by `evidence_completeness` block). Identity anchoring is strong: branch/commit `058e25b3...`, tree, `observation_hash` sha256, reproduction block with identical re-run hash. These are fixture events (`fixture_id: obs006-fixture-v1`) → `source_class: synthetic`, not ax21. Missing 22/22: timestamp, mission/incident lineage, authority, cost. Events are heterogeneous kinds (execution/acceptance/rejection/verification/integration/conflict/retry/resource/orchestration_timing); only execution/verification kinds approximate the canonical unit; resource/timing kinds are derivable attributes, not standalone observations → ~9/22 events are canonical-unit candidates; 13/22 should fold into sibling records or be rejected as standalone.

### 2.3 DSM-004 (~60 journaled events)
Hash-chained (`hash`/`prev_hash`) journals, replay-deterministic, `provenance_intact: true` in recovery suite — best-in-sample lineage integrity. But: `time_ns: 0` on every event (synthetic clock), no wall timestamps, events are transport/state transitions, not decisions. Convertible as `replay`-class provenance records of authority/state transitions; decision/outcome fields would be derived, not observed → reduced-scope use only (lineage/contamination structure, not training units).

### 2.4 RUNTIME-005 (5 fault scenarios + 2×12 conformance checks)
Contains the sample's only explicit authority material: `provider_native_authority_never_overrides_residual` scenario with a full sanitized authority map (all provider-override flags false, `residual_policy_authoritative: true`) → cleanly maps to `authority{requested,granted,violation:false}`. No timestamps. `stale_telemetry_returns_unknown` maps to `verification.status: unknown`. Good adversarial/authority-violation bench seeds (Control Bench categories 7–8), not AX-21 organic.

### 2.5 VQ-002 (~260 records; 50 sampled exhaustively from adequate part0)
Fields: `case_id, ground_truth, verdict, verifier_id, label_source: frozen_workload, safety_critical, confidence`. **Null rate: `confidence` null in 50/50 sampled records (100%)**; presumed uniform across parts (same generator), unverified for parts 1–2. No timestamps, no state, no cost. Convertible as verification-outcome records with `verification.status` from verdict/ground_truth agreement; `state` would be absent-minimal → thin training units, strong verifier-quality bench material.

### 2.6 Rejected as corpus records
- `evidence/eval/fixture-study.csv` (6 rows): config-level aggregates (P_X, aer_far, cost_usd_total, …), no per-observation linkage → REJECT 6/6 as observations; retain as run-level metadata.
- AX-21 dogfood log (#9): see §3 → REJECT as observation source (0 event-level records extractable without fabrication).
- `runs/m4-trust`, `runs/sandbox-timing`: suite/reports with `generated_at_ns` (m4-trust has `1789431995865869384` — the only real timestamp found in any sampled artifact) but records are test-suite outcomes, not state→decision→outcome units → REJECT as training units; usable as provenance/verifier_refs evidence.

### 2.7 Conversion summary
| Metric | Value |
|---|---|
| Candidate structured records sampled | 24 (OTX) + 22 (OBS) + ~60 (DSM events) + 26 (RUNTIME checks/scenarios) + 50 (VQ, of ~260) + 6 (EVAL rows) ≈ 188 directly inspected |
| Strict schema-valid conversion without invented fields | **0%** (universal `timestamp` absence; `schema_version` const absent; `authority` absent in 5/6 sources) |
| Conversion rate with (a) schema erratum: nullable `timestamp`, and (b) documented deterministic mapping, unknowns kept null | OTX 24/24; OBS ~9 canonical + 13 fold/reject; DSM ~60 as replay-class lineage records (reduced scope); RUNTIME 7 scenarios; VQ 50/50 sampled |
| Rejected records (aggregate-only or narrative) | 6 CSV rows + 1 narrative doc + 3 run-report files |
| Dominant null/unknown fields | `timestamp` 100%; `cost.inference_usd`/`energy_wh`/`operator_active_seconds` 100%; `confidence` 100% (VQ); `provenance.mission_id`/`incident_id`/`generation` ~100% (only OBS/DSM carry commit/tree identity) |

## 3. AX-21 organic evidence assessment (source #9)

The dogfood log is a contemporaneous **narrative** markdown. Contents: P1 enrollment phase (SSH-tunnel topology, host capability manifests), B0-6 lifecycle summary referencing projects `p-76cd46aacb98` / `p-d4dd2d7b4e21` with approximate clock times (~15:32:37), findings AX21-F001/F002, RES-UP candidates 001/002, P1 exit criteria, and an operator-effort ledger reported as an **aggregate of 8 interventions** (explicitly "a reported datum"; event-level entries not present).

- **Mission/incident lineage reconstruction: FAILS at event level.** Project IDs and claim/expiry/requeue sequences are described, but the underlying events, leases, receipts, and `usage.recorded` payloads are not retained in the repo. The log itself says the evidence "require[s] preservation of the underlying command/output evidence in the P1 evidence bundle" — that bundle is absent.
- **Verifiability:** claims are "reported observations" (Ghost, Wrench, Scout, KimiConductor); none independently verifiable from repo contents. Unverifiable-record rate for AX-21 source: **100%**.
- **Provenance:** `source_class: ax21` is honest, but `mission_id`/`incident_id`/`artifact_digests` are all absent → null.
- **Conversion:** 0 schema-valid observations extractable without fabricating state/decision/outcome content. Per HARD RULES, none invented.
- **Operator-effort denominator** (protocol primary metric) exists only as an unverifiable aggregate → AX-21-derived cost/operator metrics cannot be supported.

## 4. Contamination-group feasibility

- OTX: fully recoverable — natural groups by `inputs.task.task_id` family (`lookup|synthesis` × `atomic|composite|project`); retries of the same task family share config; deterministic rule possible. **Feasible.**
- VQ: recoverable via `case_id` prefix and `label_source` (frozen workload per part file). **Feasible.**
- OBS-006: single fixture = single contamination group (trivially safe). **Feasible.**
- DSM-004: groups by fault schedule/recovery scenario. **Feasible.**
- AX-21 narrative: only coarse narrative groups (B0-6 cluster; F001 stale-instruction observations ×2; P1 enrollment) — **partially recoverable, not enforceable**; with no event records this is moot unless evidence bundles are later retained.

## 5. Sanitation scan

Scanned all sampled artifacts for credentials/secrets/private data/proprietary content.
- **No credentials, tokens, or private keys found** in any sampled file. The dogfood log explicitly records key-only auth, locked password, and that "only public key shared with hub coordinator"; no key material is included. **No hard stop condition triggered.**
- ⚠️ **SOFT FLAG — infrastructure-sensitive data in source #9:** internal hostnames (LEGION, DELL7320, DBOX), LAN addresses (`192.168.5.161`, `192.168.99.2`, `192.168.1.6`), tunnel account name `residual-tunnel`, and station endpoint `127.0.0.1:8765`. Not credentials, but should be redacted/pseudonymized before any corpus inclusion per protocol redaction rules.
- Model names (`qwen2.5-coder:7b`) and hardware manifests are benign.

## 6. Format consistency

Six distinct record formats across sources (OTX JSONL, obs006.observation.v1, dsm hash-chain journals, runtime005 scenario format, VQ outcome JSONL, m4-trust/v1 reports) plus one narrative markdown. No two sources share a schema_version. Per-source deterministic converters are required; no generic converter is possible. Encoding/parse integrity: 100% of sampled JSON/JSONL parsed cleanly; no truncation or corruption observed.

## 7. Verdict and conditions

**CONDITIONAL-GO.** Conditions:

1. **Schema erratum required (SLM-00 freeze item):** make `timestamp` nullable/optional, or define a replay-class sentinel. Without it, 0% strict conversion is achievable without fabrication. This is a versioned erratum per protocol split policy, not a post-hoc edit after results.
2. **Reduced scope:** SLM corpus v0 = structured lanes only (OTX, OBS-006, DSM-004, RUNTIME-005, VQ-002) with `source_class ∈ {replay, synthetic, benchmark}`. AX-21 contributes **zero records** until P1+ evidence bundles (event-level logs, operator ledger entries, lease/receipt payloads) are actually retained. AX-21 collection per protocol §"AX-21 collection" should start emitting observation.schema.json records directly.
3. **Documented mapping + honest unknowns:** `verification.status` defaults to `unknown` unless a recorded verifier verdict exists; `authority` defaults documented as assumption; all cost subfields null except derivable `latency_ms`; no interpolation.
4. **Redaction pass** on source #9 material (§5) before any future inclusion.
5. **Contamination groups** assigned by the deterministic rules in §4 and frozen before any split.

Not GO because: timestamps universally absent (reproducible transform impossible under the frozen schema without amendment) and AX-21 organic evidence cannot currently support provenance/operator-cost requirements. Not NO-GO because: provenance anchoring (commit/tree/sha256/hash-chains) is strong, contamination grouping is recoverable for all structured sources, sanitation found no credentials, and conversion is deterministic once the timestamp erratum lands.

## 8. Reproducibility

All claims reference blob SHAs in §1. Sample conversions in §2 were performed by direct inspection of the cited blobs; no local execution environment was used (GitHub MCP read-only sampling). Record counts for VQ parts 1–2 and DSM journal totals are size-based estimates and are marked as such.
