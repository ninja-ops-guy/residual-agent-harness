# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution, fail-closed runtime handling, fresh-overlay recovery, privacy-safe local diagnostics, and an iOS/WebKit pre-boot walkthrough fallback.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main

Current `main` is **`e7b72ad18df5729f16d36771971c8a8828d71a10`**, produced by merged PR **#276** on 2026-09-19.

Recent accepted governance/qualification changes include:

- **#275** — repairs exact-PR-head publication of the protected `maintainer-approval` result after explicit exact-head human attestation. This is governance hardening, not expanded model, verifier, Factory/M4, provider or acceptance authority.
- **#276** — closes #267 by ensuring every new `main` SHA receives an authoritative production Pages qualification attempt without relying on the previous `push.paths` filter. Production Pages attempts remain non-cancelling first-attempt evidence.

The first authoritative production Pages attempt for exact current main is run **`35410875305`**, attempt 1, and is **FAIL**. The generated desktop+narrow browser proof passed, deployment passed, and the published live acceptance then failed at `Verify published WebVM revision and real guest execution`; published narrow acceptance was skipped. Retained live proof exists for that exact run. This is a production Pages qualification **FAIL** for `main@e7b72ad...`; the retained metadata does not establish a paid/live Puter failure, model-quality failure, or exact lower-level root cause.

Other exact-main automated gates must remain scoped to their own retained results. Historical failures remain evidence even when later revisions pass.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded build-output path, #183 repaired provider-session lifecycle behavior, #189 repaired the provider-helper publication boundary, #205 restores the provider channel across Mission Control reload/remount, and #248/#276 harden publication/qualification lifecycle behavior. None of those changes, by itself, is retained proof of successful paid/live Puter inference. A fresh real-account mission on the accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain open.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research evidence boundary

Research results are revision-bound and deliberately mixed:

- Draft #202 retains an earlier heterogeneous-DAG **FAIL** and a later distinct exact-head bounded **PASS** using real local models for a three-task DAG with forced repair. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.
- #220 / M6-SPEC-006 remains a bounded self-hosting **PASS** on its exact corrected research path; earlier M6-SPEC-001..004 failures remain retained negative evidence.
- #257 / M6-SPEC-007J is a bounded autonomous-discovery **PASS at formal MeasurementGap admission**. Later registry/provenance/planner experiments retain both PASS and FAIL/UNKNOWN cells. General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**.
- Draft #207/#212 stress campaigns retain accounting/release-ordering **FAIL** evidence. Those defects remain blockers for stronger fail-closed authority claims until repaired and requalified.

These are research/development observations, not production qualification. See [`docs/research.md`](docs/research.md) and [`docs/evaluation.md`](docs/evaluation.md).

## Governance boundary

Merged **#168** establishes the repository's solo-maintainer control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

Describe that as **maintainer-reviewed with automated qualification**. It is not independent human assurance. Claim-specific independent or third-party evidence remains required wherever a security, release or research claim depends on it.

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

With Docker running, the launcher serves the Station UI at `http://localhost:8765`. Native mode requires Python 3.11+ and Git:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

The accepted `setup.sh` path is an optional native convenience path; it does not remove the Python 3.11+ host prerequisite or constitute blank-machine qualification.

See [`START-HERE.md`](START-HERE.md) for installation and operator setup.

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

## Current priority gates

1. Diagnose and repair the exact-current-main production Pages **FAIL** from run `35410875305`; retain the first-attempt failure and require the next accepted main revision to qualify independently.
2. Repair and requalify the #207/#208/#212 governance-ordering defects before making stronger fail-closed budget/release claims.
3. Retain a fresh real-account Puter candidate→verifier→receipt success on the accepted deployed revision, or keep live-provider success `UNKNOWN`.
4. Physically validate the #186 mobile fallback without broadening it into heavyweight-WebVM reliability.
5. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak for the exact release artifact.
6. Continue #120/#126 long-run WebVM reliability work and the separate #139→ownership-baseline→#134 protected sequence.
7. Keep M6/M7 research bounded: unmerged discovery, derivation-graph, and recursive-mission work is not accepted production capability; general recursive self-improvement remains `UNKNOWN`.
8. Address #305 queue saturation without cancelling required first-attempt production evidence; #307 remains an unmerged candidate repair.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, autonomous recursive self-improvement, autonomous merge authority, or live proof of the central research hypothesis.