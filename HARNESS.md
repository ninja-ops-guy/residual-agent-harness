# RESIDUAL core harness

**A verifier-first harness that delegates unresolved work without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness layer. The repository has expanded into Command Station, Factory M2/M3/M4, Mission Control/WebVM, Qualification v1, evaluation infrastructure and bounded self-maintenance research. For repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## Core model

RESIDUAL decomposes a host-authored task into checked obligations. Local or remote workers propose results; the controller accepts only results that pass registered checks. Stronger or more expensive workers receive the unresolved frontier, relevant dependency values and bounded failure/evidence context rather than unilateral authority over accepted state.

```text
Goal / task
  ↓
Obligation DAG + checks
  ↓
Worker proposal
  ↓
Independent verification
  ├─ PASS → freeze accepted value + receipt
  └─ FAIL / UNKNOWN → residual + counterexample → retry / escalate
```

The worker may be capable, weak, stochastic or wrong. The controller owns acceptance.

## Run the core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
python3 -m unittest discover -s tests -v
```

The built-in demo is scripted and credential-free. It demonstrates controller behavior and evidence handling; it is not a live-model accuracy benchmark.

## Core controller invariants

| Mechanism | Implemented behavior |
| --- | --- |
| Residual frontier | Escalated workers receive unresolved, currently solvable obligations rather than already accepted independent work |
| Independent checks | Model confidence and self-declared success do not accept a result |
| Counterexample feedback | Failed checks provide bounded task-specific failure information |
| Evidence pull | Workers request permitted evidence windows rather than arbitrary source access |
| Frozen accepted values | Later responses cannot silently overwrite accepted obligations |
| Dependency receipts | Accepted values bind to relevant contracts, evidence and parent receipts |
| Revalidated cache | Cache hits are checked again against current inputs and verifier state |
| Explicit budgets | Calls, request bytes and output limits are bounded before provider I/O |
| Honest accounting | Reported usage, modeled estimates and unknown usage remain distinct |
| Claim discipline | `FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions and provider errors do not become `PASS` |

## Relationship to the broader platform

- **Command Station** provides operator-facing mission/run/provider control.
- **Factory M2** provides bounded worker contracts/runtime and host-owned termination.
- **Factory M3** provides Station-issued evidence/receipt handoff.
- **Factory M4** provides deterministic integration/scheduler authority and capable-runner qualification machinery.
- **Mission Control/WebVM** provides browser-facing real-guest workflows, artifact interaction, provider transport, recovery, diagnostics, and an iOS/WebKit pre-boot walkthrough fallback.
- **Qualification v1** binds required release-test evidence to exact source/tree/environment identity and aggregates deterministic, stateful, history, fault, mutation, coverage, M4, wheel/container and browser gates fail closed.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles and economics/observability surfaces.

## Current repository boundary

Current `main` is **`91d32fd8b713c68c1cd2e473013c9e1c33b93572`**.

Qualification v1 and its focused runner/product-path repairs converged through **#152**, **#355**, and **#356**. **#397** is now accepted repository state as well: the WebVM standalone-workbench durability fix was exact-head attested and merged, producing `main@91d32fd8...`.

On this exact main revision, the observed push-triggered **RESIDUAL Qualification v1**, **Deploy GitHub Pages**, **Controller and provider contracts**, **Command Station checks**, **clean-install qualification**, and **M4 qualification runner prerequisites** are **PASS**. Vercel is also **PASS**. The previous `main@b571b91...` Pages post-deploy failure remains retained historical FAIL evidence; the first authoritative Pages run on the repaired `main@91d32fd8...` passed.

Do not inherit those results beyond their evidence scope. Qualification v1 does not manufacture elapsed soak, live-provider, physical-device, every-host, independent-security, or owner-acceptance evidence for other revisions.

Historical failures remain retained evidence rather than being erased by later PASS results.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179, #183, #189, #205 and #397 repair bounded build-output, provider-session, publication, reload-recovery and hosted WebVM durability surfaces. None is retained proof of successful paid/live Puter inference. A fresh exact-deployed-revision real-account mission must reach normal candidate/verifier/receipt handling before live-provider success becomes `PASS`.

The #186 fallback remains accepted: detected iOS/iPadOS WebKit is routed to the lightweight walkthrough before heavyweight guest boot. Physical heavyweight-WebVM reliability and the lower-level process-kill cause remain **UNKNOWN / unqualified**. Issues #120/#126 remain separate.

## Factory and trust-boundary constraints

M2/M3/M4 are implemented and `implementation-status.yaml` remains an implementation-presence manifest. M4 qualification is exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

The accepted Qualification-v1 convergence carries the owner-authorized #152 portability ownership advance: platform-neutral `residual/factory/m4_protocol.py` is part of the protected core set and the ownership baseline records that pin alongside the previously authorized RuntimeJournal pin. That accepted baseline advance is exact-byte governance evidence, not a general relaxation of M4 or sandbox authority.

This documentation does not alter Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Release-security boundary

Open owner issue **#353** remains the dedicated **P0 release blocker**, with focused implementation candidate **#399** based on accepted `main@91d32fd8...`.

#399 proposes repairs for AUD-1 F1/F2/F3/F4/F6 and the required ten-adversarial-regression surface. That is **candidate implementation evidence**, not closure. The prior exact head `fb416efe29d245fcbbb03f6f8edb8c89a8212f3d` had green technical CI, but PR-Agent identified that adversarial requirement #6 lacked an explicit positive coordinator-transition regression. Those exact-head PASS results remain retained evidence but are superseded for final qualification rather than broadened into acceptance.

Current #399 exact head is **`8df77b832b3839ccd2a6944a65760ce3ab10dc9c`**. It adds only the missing coordinator-vs-worker transition regression. Fresh exact-head evidence is:

- Factory ownership: **PASS**
- Control Plane: **PASS**
- clean-install qualification: **PASS**
- PR-Agent advisory: **PASS**
- Controller/provider contracts: **PASS**
- Command Station checks: **PASS**
- Pages PR-head/browser proof: **PASS**
- measured-evaluation binding: **PASS**
- Vercel: **PASS**
- RESIDUAL Qualification v1 aggregate: **PASS**
- exact-head maintainer approval: **FAIL / no matching human attestation**

The owner has therefore classified the #399 **software gate as ready for physical P1 dogfood** on this exact candidate. That is not a merge authorization and does not close #353.

The retained candidate history remains exact-revision evidence: earlier `3fee648...`, `a7f1068...`, and `8294b824...` failures remain historical FAIL evidence for those revisions; `fb416efe...` remains technical PASS evidence that was superseded for final acceptance when the missing explicit regression was found. None is rewritten by the current PASS.

The candidate remains **UNACCEPTED / NOT MERGE-READY**. The #353 convergence order remains authoritative:

`implementation → ten adversarial regressions → normal repository CI → physical P1 F6 inside/outside-window dogfood → independent re-audit → exact-head qualification → owner attestation → merge → authoritative new-main qualification`

The two physical F6 cases remain required and distinct on the real LEGION / DELL7320 / DBOX topology: reconnect inside the retry/authority window must prove continuity without duplicate authority/invalid transition, and reconnect outside the authority window after expiry/reassignment must prove the old worker/result remains dead. Until separately retained artifacts exist, both claims remain **UNKNOWN / not established**.

Mason/LEGION's read-only re-audit remains required after the physical evidence and before acceptance. Current exact-head Qualification-v1 PASS cannot be used to skip that order, and any candidate-byte change invalidates affected qualification/audit evidence.

## Research boundary

Research evidence remains revision-bound and deliberately mixed. Automated SLM-00 Lane G/G2 evidence may be positive for one exact candidate while the research program remains **NOT FROZEN / UNACCEPTED / NO-TRAINING**. Automated review does not synthesize human freeze or maintainer authority.

Draft research PR **#401** is an append-only AX-21/SLM-00 evidence check-in on `research/exp-m6-slm-00`. It records additional research observations but explicitly does not freeze SLM-00, authorize training, close AUD-1, or advance release authority.

These observations do not establish autonomous recursive self-improvement or production reliability.

## Governance boundary

Merged #168 establishes the repository's solo-maintainer approval model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

It is **maintainer-reviewed with automated qualification**, not independent human assurance. A release, security or scientific claim may still require independent evidence.

## Evaluation guidance

The scripted benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, token savings or API cost. Confirmatory research must bind results to exact source, workload, execution identity, verifier policy and retained artifacts.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/testing/QUALIFICATION_V1.md`](docs/testing/QUALIFICATION_V1.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Current scope and non-claims

A passing check establishes only its declared condition. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, guaranteed savings, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, closed AUD-1 security convergence, autonomous recursive self-improvement, autonomous merge authority, or proof of the central live-model reliability hypothesis.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
