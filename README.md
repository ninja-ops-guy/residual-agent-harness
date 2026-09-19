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

Current `main` is **`0a675017a51f94e489528a607032e7463fbf7993`**, produced by merged **#328** on 2026-09-19.

Recent accepted changes relevant to current claims are deliberately scoped:

- **#307** — removes duplicate generic feature-branch `push` fan-out from the general CI paths while preserving PR qualification and non-cancelling production-main evidence. The acute Actions backlog is currently **0 queued runs**; that does not erase earlier queue evidence.
- **#260** — accepts the provider-bootstrap guard that keeps the Puter load control disabled until its private bridge is initialized. This is a bounded UI/transport repair, not paid/live Puter evidence.
- **#288** — closes #208 with host-owned pre-dispatch budget/deadline admission for Station runner/reviewer dispatch plus bound run-control export eligibility. Historical #207/#212 negative research cells remain retained and require claim-specific requalification rather than being rewritten as PASS.
- **#320** — adds repository-side CSP/anti-clickjacking hardening. Vercel can emit the configured response headers; GitHub Pages retains only the HTML CSP fallback because arbitrary repository-controlled response headers are not available there. Production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328** — accepts the core, non-workflow split of the #324 security pass: kernel-enforced third-party execution isolation, connector SSRF/bearer hardening, hardened SAML XML parsing, and bounded marketplace/recovery/telemetry/demo-gateway changes with regression coverage. The separate workflow credential-persistence changes remain open under #324.

Every new `main` SHA is required by the accepted #276 gate to receive its own non-cancelling first production Pages attempt. For exact current main, production Pages run **`35431634267`**, attempt 1, completed **PASS**. The `build-and-browser-proof` job passed, deployment passed, published WebVM revision plus real guest execution passed, and the narrow Chromium acceptance passed. Retained artifacts include `webvm-live-proof-35431634267-1` (`10580449851`, SHA-256 `ebdecf8e4055679933f1941f648d422d37a38ba5e4dad1f285967b83ccf684aa`) and `webvm-proof-35431634267-1` (`10580818938`, SHA-256 `9ed51067d6fc7d1222edc9eec9c7a265d880e9a30f7080ba7f90ffe360627f06`). The earlier production Pages **FAIL** on `e7b72ad...` remains historical evidence for that exact revision and is not erased by this PASS.

That exact-main Pages result is a **PASS only for its publication/browser/real-guest qualification scope**. It does not establish paid/live Puter inference, model quality, physical heavyweight-WebVM iPhone reliability, every-host M4 qualification, or blanket production readiness.

Historical failures remain evidence even when later revisions pass.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179, #183, #189, #205, #248, #260 and #276 repair bounded build-output, provider-session, bootstrap, publication and qualification surfaces. None is retained proof of successful paid/live Puter inference. A fresh real-account mission on an accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain open.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research evidence boundary

Research results are revision-bound and deliberately mixed:

- Draft #202 retains an earlier heterogeneous-DAG **FAIL** and a later distinct exact-head bounded **PASS** using real local models for a three-task DAG with forced repair. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.
- #220 / M6-SPEC-006 remains a bounded corrected-path self-hosting **PASS**; earlier M6 self-host trials retain **FAIL** evidence.
- #257 / M6-SPEC-007J is a bounded autonomous-discovery **PASS at formal MeasurementGap admission**. Later registry/provenance/planner experiments retain PASS, FAIL and UNKNOWN cells. General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**.
- #207/#212 retain historical accounting/release-ordering and failure-matrix evidence. The accepted #288 repair closes the product defect tracked by #208, but it does not retroactively change those frozen research outcomes; affected claims require fresh requalification on the repaired path.
- #319 / M6-MESH-001 is one positive bounded two-obligation concurrency pilot; general mesh/swarm efficiency remains **UNKNOWN / not established**.
- Draft #323 Research Workbench remains **BLOCKED for its first authoritative trial**: #288 is now accepted, satisfying one prerequisite, but #323 is still based on the older `e7b72ad...` main and must be rebased and requalified before an authoritative Workbench run.

M6-008 remains **BLOCKED** until its declared semantic/derivation gates are satisfied. These are research/development observations, not production qualification. See [`docs/research.md`](docs/research.md) and [`docs/evaluation.md`](docs/evaluation.md).

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

1. Requalify any stronger budget/unknown-usage/release-ordering claim that depended on the historical #207/#208/#212 failures against the accepted #288 repair; historical frozen failures remain visible.
2. Rebase and requalify #323 on a main containing #288 before any first authoritative Research Workbench trial.
3. Validate the merged #320 policy on the production Vercel origin and rerun the relevant security check before calling response-header remediation PASS in production.
4. Finish the remaining #324 workflow credential-persistence hardening independently of the accepted #328 core security split.
5. Retain a fresh real-account Puter candidate→verifier→receipt success on an accepted deployed revision, or keep live-provider success `UNKNOWN`.
6. Complete physical mobile fallback validation, true blank-environment installation, recovery/host-loss qualification, selected elapsed soak, and #120/#126 long-run WebVM reliability work without broadening bounded evidence.
7. Keep M6/M7 research bounded: general recursive self-improvement and general mesh efficiency remain `UNKNOWN`; M6-008 remains `BLOCKED`.
8. Preserve production Pages run `35431634267`, attempt 1, as the exact-revision **PASS** for its publication/browser/real-guest scope without using it to infer provider, model, physical-device, or unrelated trust-boundary success.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, autonomous recursive self-improvement, autonomous merge authority, production Vercel security-header validation, or live proof of the central research hypothesis.
