# RESIDUAL core harness

**A verifier-first harness that delegates unresolved work without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness layer. The repository has expanded into Command Station, Factory M2/M3/M4, Mission Control/WebVM, evaluation infrastructure and bounded self-maintenance research. For repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

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
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles and economics/observability surfaces.

## Current repository boundary

Current `main` is **`0a675017a51f94e489528a607032e7463fbf7993`**, produced by merged **#328** on 2026-09-19.

Accepted changes since the earlier documented boundary include **#307** (duplicate feature-branch CI fan-out repair), **#260** (provider bootstrap guard), **#288** (pre-dispatch Station budget/deadline admission and run-control-bound export eligibility), **#320** (repository-side CSP/anti-clickjacking policy), and **#328** (core non-workflow execution/egress/XML security hardening). These are bounded engineering/governance/security changes; none expands model, verifier, Factory/M4 or evidence-schema authority.

Every current `main` SHA now receives its own non-cancelling production Pages attempt under accepted #276. Exact-current-main run **`35431634267`**, attempt 1, completed **PASS**. Its `build-and-browser-proof` job, deployment, published WebVM revision/real-guest execution check, and narrow Chromium acceptance all passed. Retained live proof is artifact `10580449851`, SHA-256 `ebdecf8e4055679933f1941f648d422d37a38ba5e4dad1f285967b83ccf684aa`. The earlier Pages **FAIL** on `e7b72ad...` remains historical exact-revision evidence and is not erased.

This PASS is scoped to exact-revision publication/browser/real-guest qualification. It does not establish live provider/model quality, physical heavyweight-WebVM iPhone reliability, every-host M4 qualification, or blanket production readiness.

The accepted #288 repair closes product issue #208. Historical #207/#212 stress/failure-matrix outcomes remain retained evidence and are not rewritten by the merge; any stronger budget/unknown-usage/release-ordering claim needs fresh qualification on the repaired revision.

The accepted #320 policy is repository configuration, not yet production Vercel response-header acceptance. Production header inspection/Aikido revalidation remains **UNKNOWN / pending**. #328 accepts the core non-workflow portion of #324; the remaining workflow `persist-credentials: false` hardening is now isolated in focused current-main PR **#330**, which remains **OPEN / unaccepted**. The stale overlapping #324 must not be merged wholesale.

Historical failures remain retained evidence rather than being erased by later PASS results.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179, #183, #189, #205, #248, #260 and #276 repair bounded build-output, provider-session, bootstrap, publication and qualification surfaces. None is retained proof of successful paid/live Puter inference. A fresh exact-deployed-revision real-account mission must reach normal candidate/verifier/receipt handling before live-provider success becomes `PASS`.

The #186 fallback remains accepted: detected iOS/iPadOS WebKit is routed to the lightweight walkthrough before heavyweight guest boot. Physical heavyweight-WebVM reliability and the lower-level process-kill cause remain **UNKNOWN / unqualified**. Issues #120/#126 remain open.

## Factory and trust-boundary constraints

M2/M3/M4 are implemented and `implementation-status.yaml` remains an implementation-presence manifest. M4 qualification is exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

Accepted #185/#187 protected changes retain their reviewed scope. Keep them distinct from the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence. A green hosted lane does not establish every-host qualification.

This documentation does not alter Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research boundary

Recent research evidence must remain mixed:

- #202: earlier retained heterogeneous-DAG **FAIL**; later bounded corrected exact-head **PASS** with real local models and forced repair. Neither result erases the other.
- #220: bounded corrected M6-SPEC-006 self-hosting **PASS**; earlier M6 self-host trials retain **FAIL** evidence.
- #257: bounded M6-SPEC-007J formal MeasurementGap-admission **PASS**; later registry/provenance/planner work includes PASS, FAIL and UNKNOWN cells. General autonomous discovery remains **UNKNOWN / not established**.
- #207/#212: frozen stress/failure-matrix evidence includes accounting/release-ordering and missing-usage failures. #288 repairs the tracked product defect (#208), but the research cells remain historical and require repaired-path requalification for stronger claims.
- #319: one bounded concurrency pilot is positive, while general mesh/swarm efficiency remains **UNKNOWN / not established**.
- #323: Research Workbench is still draft and its first authoritative trial remains **BLOCKED** pending rebase/requalification onto a main that includes the now-accepted #288 repair.
- M6-008 and broader recursive self-improvement remain **BLOCKED/UNKNOWN** until their specific positive gates are satisfied. Unmerged M6/M7 branches are not accepted product capability.

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
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Current scope and non-claims

A passing check establishes only its declared condition. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, guaranteed savings, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, production Vercel header validation, autonomous recursive self-improvement, autonomous merge authority, or proof of the central live-model reliability hypothesis.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
