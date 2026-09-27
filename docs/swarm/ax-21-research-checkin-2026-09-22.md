# AX-21 Research Check-In — 2026-09-22

**Program:** RESIDUAL / AX-21
**Type:** Append-only research-maintenance record
**Baseline comparison:** AX-21 pre-release baseline / candidate AX-21-BASELINE-R0
**Accepted main observed:** `91d32fd8b713c68c1cd2e473013c9e1c33b93572`

This record preserves only material changes observed since the prior AX-21 research check-in. It does not mutate the baseline, claim a release, close AUD-1, claim post-#349 operator-friction improvement, or promote apparatus into empirical evidence.

## 1. Measured R0-R5 ablation apparatus now exists, but no confirmatory result exists yet

PR #402 (`research/residual-ablation-001`, head `2958ef726cab4deaaa997c0bf4b426a74349213e`) introduces a separately governed measured R0-R5 experiment path rather than relabelling the existing scripted `residual.eval_frozen` fixture as empirical evidence.

Observed apparatus properties include:
- complete paired `(task, repeat) x R0-R5` enforcement;
- held provider/model/prompt/inference/tool/grader/environment/budget hashes;
- ASSR and safety UAR endpoints plus reliability/efficiency counters;
- explicit UNKNOWN retention;
- prohibition on outcome-dependent early stopping;
- immutable evidence references and content-addressed bundles;
- preregistration material and tests for pairing, missingness, manifest binding, state consistency, tamper detection, and fault evidence.

**Research interpretation:** this materially strengthens the separation between development fixtures and confirmatory evidence. It does **not** yet support H1 or any reliability-effect claim because no live measured workload has been frozen/executed through the required real Factory adapter.

**Negative/limiting evidence retained:** current PR status includes an external Vercel daily deployment-rate failure. This is infrastructure noise, not a scientific result, and should not be confused with experiment failure. The scientific gate remains execution-adapter binding plus frozen workload before outcome access.

## 2. AUD-1 physical F6 evidence collection became more rigorous, but F6 remains UNKNOWN

PR #403 (`tools/aud1-f6-physical-diagnostics`, current head `03a89dfe0c76e4eaea1406304e9f41a78255a402`) adds a read-only evidence kit for the two outstanding physical F6 cases against exact #399 candidate `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`.

The tooling binds evidence to exact candidate SHA/tree/clean-worktree state and captures read-only Station snapshots, task owner/lease/expiry, event-chain tails, redacted settings, bootstrap metadata, operator timeline, remote diagnostics, hashed attachments, and immutable manifests.

The harness deliberately does not claim, heartbeat, submit, replay, edit leases/SQLite, recover tasks, rotate credentials, approve, integrate, or declare PASS. The operator controls the real tunnel interruption/restoration. F6-B preserves the real 180-second worker grace and 900-second server lease instead of accelerating time or editing lease state.

Two independently frozen bundles are required:
- `F6-A-inside-window`
- `F6-B-outside-window`

A later documentation reconciliation records that the current #403 exact head passes the technical qualification surfaces it enumerates, while exact-head maintainer approval is still absent and **both physical F6 bundles remain UNKNOWN/not established**. Issue #353 therefore remains P0/BLOCKED.

### Preserved negative result

An earlier #403 head (`10a355fc...`) had a retained deterministic qualification failure. The current head advanced through focused redaction repairs, including explicit authorization-scheme credential redaction. The failed revision remains part of the evidence history and is not rewritten by the later green head.

**Research interpretation:** AX-21's earlier fail-closed findings remain scoped to tested lease/claim/result surfaces. Physical authority-loss/reconnection behavior is still unproven until the two real tunnel experiments and independent read-only re-audit exist.

## 3. Shared Comms / mesh architecture is beginning to absorb AX-21 coordination and identity findings

PR #404 (`sc-mesh-001-v0.1`, head `cae9ab31e0ca3acfd948af32726db388c589aeb2`) implements the first isolated candidate slice of SPEC-SC-MESH-001.

Observed candidate features include:
- typed per-worker enrollment with project/capability scope;
- per-enrollment bearer credentials stored only as hashes;
- explicit ENROLLED -> SYNCING -> READY / DISCONNECTED / REVOKED lifecycle;
- bounded versioned message envelopes;
- durable namespaced idempotency, replay cursors, and dead letters;
- crash-durable worker outbox/inbox;
- project generation and monotonic task fencing-token foundation;
- presence-only mesh heartbeat that does not renew task authority;
- scoped mesh worker HTTP surfaces;
- regression coverage for authority smuggling, replay, conflict, revocation, generation staleness, fencing, stop, and HTTP round-trip.

This aligns with multiple AX-21 findings: the current shared-key identity weakness, the need to keep presence distinct from authority/evidence, and the hidden operator burden of distributed coordination.

**However, the candidate explicitly does not claim live deployment, MESH_QUALIFIED status, merge authorization, completed W4 assignment-budget integration, W5 provider continuity/host containment/evidence binding, or W6/W7 multi-host qualification.**

Advisory review also raised transport/integrity/clock-handling questions. These remain review items, not established defects, until independently reproduced or resolved by exact-head review/testing.

**Research interpretation:** #404 is architecture derived from AX-21 findings, not evidence that operator-friction, autonomy, or distributed reliability has improved. It becomes research evidence only after a controlled multi-host reproduction against the AX-21 baseline.

## 4. P5 operator-friction result has not advanced

PR #349 remains open/draft. The frozen before-condition therefore remains authoritative:
- Station cannot answer the global swarm-state question directly;
- approximately 11 cold individual-agent queries plus human synthesis are required;
- normal operation relied on 15+ manual reports/session and external ledgers.

No post-#349 replay measurement should be reported yet.

## 5. AX-21 final baseline freeze has not occurred

The repository currently has no formal GitHub release. Therefore the release-tag cutover required for final `AX-21-BASELINE-R0` freeze has not occurred.

The AX-21 pre-release record remains the control condition/candidate baseline, not a finally frozen post-release dataset.

## 6. New or strengthened research hypotheses / RES-UP candidates

The following remain candidates unless/until assigned registry identifiers:

### Candidate RES-UP — Confirmatory-ablation execution binding
Require a real execution adapter, frozen workload, exact execution manifest, and outcome-blind freeze before any measured R0-R5 result is exposed. Prevent scripted fixture outputs from being promoted into empirical claims.

### Candidate RES-UP — Physical authority-loss evidence as a first-class artifact
Standardize F6-style physical disruption experiments as two-part frozen evidence bundles with exact candidate identity, operator timeline, remote-host evidence, and independent read-only re-audit.

### Candidate RES-UP — Evidence-tool redaction qualification
Evidence collectors that may capture diagnostics/settings should carry explicit credential-redaction regression tests and preserve first-failure history. Redaction failures are evidence-system defects, not clerical issues.

### Candidate ImprovementSpec — Mesh qualification against AX-21 coordination baseline
Once the mesh candidate is technically complete, run a controlled three-host reproduction that measures whether it reduces operator actions/queries and external ledger dependence while preserving authority separation, evidence traceability, and stale-state rejection.

### Candidate ImprovementSpec — Presence/authority non-interference
Formally test that mesh presence heartbeats cannot extend task authority, alter leases, or satisfy evidence/review gates under delay, replay, restart, clock skew, and reconnection.

## 7. Paper-relevant conclusions

### Supported by current evidence
- Development fixtures and confirmatory empirical evidence are now being separated more explicitly in the experiment design.
- AUD-1 physical authority-loss testing has a stronger evidence-preservation protocol, but the required physical results do not yet exist.
- RESIDUAL's architecture is beginning to encode lessons from AX-21 around per-worker scope, replay/idempotency, presence-vs-authority separation, and durable distributed communication.
- Negative results continue to be preserved across candidate revisions rather than erased by later green runs.

### Not yet supported
- No claim that R0-R5 materially improves reliability in live measured execution.
- No claim that AUD-1 F6 physical reconnection/authority-loss behavior passes.
- No claim that the mesh reduces operator friction or increases autonomy.
- No claim that AX-21-BASELINE-R0 is finally frozen.
- No claim of whole-system security.

## 8. Next evidence gates

1. Execute and freeze the two physical F6 tunnel cases against exact #399 candidate bytes, then obtain independent read-only re-audit.
2. Bind PR #402 to a real Factory execution adapter and freeze the first measured confirmatory workload before outcome access.
3. Complete the mesh candidate's W4-W7 gaps, then run a controlled multi-host qualification against the frozen AX-21 operator-friction question.
4. Keep the exact P5 question unchanged for post-#349/mesh comparison.
5. Do not declare final AX-21 baseline freeze until an actual release-tag cutover and complete evidence manifest exist.
