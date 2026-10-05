# AX-21 Research Findings — Pre-Release Baseline

**Program:** RESIDUAL  
**Experiment:** AX-21 Federated Swarm / BOOTSTRAP-0 / P1  
**Observation period:** 2026-09-19–2026-09-20  
**Environment:** LEGION (WSL2), DELL7320, DBOX  
**Status:** Baseline findings frozen pending first defensible RESIDUAL release

## Research objective

AX-21 studies whether a heterogeneous agent swarm can perform useful software engineering and R&D work while an external control plane constrains authority, verifies outputs independently of agent claims, preserves provenance, fails closed when authority becomes invalid, supports heterogeneous/local inference, reduces human coordination, and eventually supports evidence-governed recursive improvement.

Core distinction: **Generation != Authority != Verification != Integration.**

## Findings

### F-01 — Useful work and fail-closed control coexisted

A local 7B model completed the observed claim -> execution -> verified-candidate path in approximately **16.4 seconds** during B0-6 without a verifier exception. Negative testing rejected bogus-lease heartbeat, bogus-lease result submission, post-race claim, and invalid explicit-task claim. Candidate state remained protected; lease expiration moved work to BLOCKED; recovery used blocked -> proposed -> triaging -> ready without direct DB surgery.

**H1 — Verified autonomy:** useful agent work may proceed under fail-closed authority and independent verification without routine bypass. AX-21 provides preliminary support only for tested surfaces.

### F-02 — Station evidence was more reliable than agent consensus

B0-5 showed materially different worker failures collapsing into the same generic message. An incorrect root-cause hypothesis propagated before retained evidence and independent reproduction falsified it.

**H2 — Evidence over consensus:** persistent authoritative evidence may improve recovery from incorrect multi-agent consensus relative to agent self-report alone. Controlled comparison remains future work.

### F-03 — Diagnostic quality is an autonomy constraint

Authentication, provider/model, and connectivity failures were masked behind one message, preventing reliable autonomous recovery selection.

**P0:** introduce a stable machine-readable taxonomy such as `WORKER_AUTH_FAILED`, `PROVIDER_REQUEST_FAILED`, `PROVIDER_CAPABILITY_UNSUPPORTED`, `NETWORK_UNREACHABLE`, `NETWORK_TIMEOUT`, and `CONTRACT_REJECTED`, with safe diagnostic context.

### F-04 — Credential consumption had a reproducible interface trap

The generated key file used `export RESIDUAL_WORKER_TOKEN=...`; consuming the whole file as the token produced HTTP 403. Two workers hit this independently.

**P0:** automation-safe `--token-file` handling and/or canonical `residual worker-key`. Retain raw-token, export-formatted, whitespace/newline, malformed/missing, rotation-rejection, and secret-safe diagnostic cases.

### F-05 — Lease expiration is correct but counterintuitive

Observed behavior: lease expires -> task BLOCKED -> owner cleared -> explicit triage. An incorrect auto-requeue assumption propagated to multiple workers.

**P0-DOC:** document semantics and surface blocked-lease tasks. Audited policy-driven auto-requeue remains post-release.

### F-06 — Presence, telemetry, and evidence are distinct

Heartbeats were operationally useful but not independently reconstructable like claims/submissions. Acceptance criteria must distinguish ephemeral presence, persisted event evidence, and receipts.

### F-07 — Human coordination was hidden infrastructure

For the frozen question, **"What is every agent doing right now, where is it running, what is it waiting on, and what does it need from me?"**, the Station could not answer directly. Cold reconstruction required approximately **11 individual agent queries plus synthesis**; normal operation depended on continuous synthesis of **15+ manual reports/session** into external ledgers.

The operator was functioning as a distributed-state reconciliation layer.

### F-08 — Autonomy is multidimensional

Bounded execution was highly autonomous and verification/authority system-controlled; diagnosis/recovery/scheduling were mixed; global-state reconstruction/bootstrap were human-heavy; release authority remained human-controlled. Report autonomy by function rather than a binary or arbitrary score.

### F-09 — Early recursive-improvement behavior was observed

AX-21 produced: operate -> encounter deficiency -> preserve evidence -> investigate -> reject incorrect hypotheses -> derive requirement/ImprovementSpec -> create implementation lane -> retain reproduction corpus -> schedule qualification rerun.

This is preliminary evidence of a recursive improvement loop, **not** sustained autonomous recursive development.

### F-10 — Provider capability discovery is incomplete

LM Studio rejected the required `response_format=json_object` path in the tested configuration; Ollama provided the proven local path.

**P1:** capability probing/negotiation and safe fallback or explicit capability failure.

### F-11 — Fresh-machine qualification is necessary

Dogfooding exposed setup artifacts, missing imports, stale dispatch, and public CLI/documentation drift.

Official first-use qualification should reproduce: install -> init -> configure provider -> obtain credential -> enroll -> create project -> claim -> execute -> heartbeat -> submit -> verify -> review_ready -> rotate credential -> prove old credential rejection -> inspect evidence -> expire lease -> documented triage recovery.

### F-12 — WSL2 behavior can masquerade as runtime failure

Observed issues included idle VM termination, invocation expansion traps, and Windows-host/local-model relay requirements.

**P0-DOC:** systemd/autostart, idle behavior, script-file invocation, host/guest networking, relay patterns.

### F-13 — Worker identity must be documented honestly

The current model uses a shared bearer credential with name/context distinction. Rotation invalidates the old credential, but strong independent per-worker identity/revocation is not yet present.

## P5 operator-friction baseline

Frozen before-condition:

- Station answers directly: **No**
- Cold individual-agent queries: **11**
- Human synthesis: **Required**
- External coordination state: **Required**
- Continuous reports synthesized: **15+ per session**

After #349, replay the identical question and measure agent queries, operator actions/time, model calls, roster coverage, stale-state rate, external sources, authoritative vs self-reported fields, and evidence traceability.

**H3 — Coordination transfer:** authoritative machine-maintained swarm state may reduce human reconciliation work without reducing correctness or traceability.

## Heterogeneous inference research direction

Compare: (A) high-capability model everywhere, (B) local/small model everywhere, and (C) RESIDUAL hierarchical routing. Measure verified success, verifier rejection, escalation, intervention, latency, inference cost, compute utilization, and evidence completeness.

**H4 — Hierarchical inference efficiency:** capability-aware routing may approach high-capability verified performance at lower inference cost. AX-21 establishes feasibility observations only.

## Release boundary

**P0:** worker failure classification; safe token consumption; #347 clean-machine qualification; #348 public CLI correctness.

**P0-DOC:** lease-expiry semantics; presence vs durable evidence; WSL2 notes; worker-key/identity model.

**P1:** provider capability negotiation; LM Studio compatibility/fallback; audited auto-requeue; per-worker credentials/revocation.

**Scope guard:** #349/P5 may proceed, but dashboard expansion should not delay release unless required for safe operation.

## Reproduction corpus

Retain regression assets for HTTP 403 auth failure, model/provider failure, export-prefix variants, credential-rotation rejection, stale/bogus lease operations, post-race claim rejection, explicit-task claim rejection, and lease-expiry/triage recovery.

## Threats to validity

Researcher/operator coupling; three-host environment; task-domain bias toward RESIDUAL; model/provider dependence; learning effects; non-independent interacting agents; moving apparatus; success-selection bias.

Mitigations: raw evidence retention, preregistered comparisons, frozen releases/datasets, preserved negative results, and independent reproduction.

## Research tracks

1. **Verified Agentic Control**
2. **Human Coordination Cost**
3. **Evidence-Guided Recursive Improvement**
4. **Hierarchical Model Allocation**

## Baseline freeze

When the first defensible release is tagged, AX-21 SHALL be frozen as **AX-21-BASELINE-R0** with exact release/repository identities, host/environment manifests, provider/model configuration, experiment/calibration logs, Station DB/event evidence, qualification results/receipts, negative-test corpus, failures, falsified hypotheses, operator interventions, external ledgers, P5 baseline, B0/P1 evidence, derived RES-UP/ImprovementSpec artifacts, release defects, known limitations, and final P0/P0-DOC/P1 disposition.

The baseline represents the system **as actually operated**. It must not be retrospectively cleaned or normalized. Later corrections are append-only annotations preserving the original observation and evidence.

Baseline invariants: environment identity is reconstructable; findings trace to retained evidence; failures/manual recovery remain represented; human intervention remains counted; later evidence is not substituted into AX-21; corrections are append-only; pre-release defects, release fixes, and post-release improvements remain distinguishable.

The release tag is the experimental cutover. Changes landing afterward belong to the next generation even when motivated by AX-21.

The release-tagged reproduction across LEGION, DELL7320, and DBOX must record every documentation ambiguity, manual repair, configuration intervention, credential issue, escalation, retry, failed recovery, external-ledger lookup, operator clarification, and qualification failure.

Post-release comparisons should retain individual measures rather than collapse them into an arbitrary autonomy score: human interventions per accepted improvement, active minutes, actions, agent queries, external dependencies, model calls, local/remote inference, wall-clock time, retries, blocked tasks, incorrect hypotheses, verifier rejections, recovery events, cost, evidence completeness, authority bypasses, and verified task success.

AX-21 may be declared **FROZEN** only when the release boundary is unambiguous, evidence/manifest are complete, failures/interventions and P5 baseline are preserved, reproduction corpus is retained, unresolved limitations are listed, comparison artifacts are version-identifiable/hash-bound where practical, the dataset is read-only or append-only, and the next experiment has a distinct identifier.

## Research conclusion

AX-21 does not establish autonomous recursive development or general system security. It establishes an empirical map of where agent autonomy currently succeeds, where humans remain infrastructure, where agent explanations can fail, and where an inspectable verifier-first control plane can constrain useful autonomous work without routine authority bypass on the tested surfaces.

Emerging loop: **Operate -> Observe -> Preserve -> Challenge -> Specify -> Implement -> Verify -> Measure**

Future generations should be judged against AX-21 by measurable reductions in human coordination, unnecessary escalation, cost, and recovery burden while maintaining or improving verified work, evidence completeness, and authority/verification boundaries.

The central longitudinal research question is the **progressive transfer of coordination and improvement work from humans to autonomous systems under persistent evidence, bounded authority, and independent verification.**

**AX-21-BASELINE-R0 remains a candidate for freeze upon completion of the release-tagged reproduction and evidence manifest.**
