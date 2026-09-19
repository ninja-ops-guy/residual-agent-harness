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

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged **#330** on 2026-09-19.

Recent accepted changes relevant to current claims are deliberately scoped:

- **#307** — removes duplicate generic feature-branch `push` fan-out from general CI while preserving PR qualification and non-cancelling production-main evidence.
- **#260** — accepts the provider-bootstrap guard that keeps the Puter load control disabled until its private bridge is initialized. This is bounded UI/transport behavior, not paid/live Puter evidence.
- **#288** — closes #208 with host-owned pre-dispatch budget/deadline admission for Station runner/reviewer dispatch plus run-control-bound export eligibility. Historical #207/#212 negative research cells remain retained and require claim-specific requalification rather than being rewritten as PASS.
- **#320** — adds repository-side CSP/anti-clickjacking hardening. Production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328** — accepts the core non-workflow portion of the security-hardening pass: kernel-enforced third-party execution isolation, connector SSRF/bearer hardening, hardened SAML XML parsing, and bounded supporting controls.
- **#330** — accepts the remaining GitHub Actions checkout credential-persistence hardening. Checkout steps now use `persist-credentials: false` with structural regression coverage while preserving the accepted #307/#267 workflow semantics. This is a scoped workflow-security change, not blanket security qualification. The stale overlapping #324 branch must not be merged wholesale.

Every new `main` SHA is required by accepted #276 to receive its own non-cancelling first production Pages attempt. For exact current main `3bfa6aba...`, production Pages run **`35437556200`**, attempt 1, completed **FAIL**. Build/browser proof, deployment, published revision identity, and the desktop real-guest acceptance path passed; the required narrow/mobile Chromium acceptance failed after reaching the live guest and several Workbench stages. The retained live-proof artifact is `10582812524` with SHA-256 `868ca31506d278a335ff95d3607adbd13c14edaec8b161c1b45ac013e7f7c8b8`. The lower-level cause is **UNKNOWN** and must not be attributed to #330, Puter/model quality, Factory/M4, or another subsystem without further evidence. Production Pages run `35431634267`, attempt 1, remains a scoped **PASS for exact revision `0a675017...` only**; the still earlier `e7b72ad...` production Pages **FAIL** also remains retained exact-revision evidence.

Focused repair **#336** is open at exact head `92aca285a9287b73787b552f87aaa42062e73ba4`. It adds an explicit guest-filesystem durability boundary before the browser worker publishes its reusable completion marker. Its generated PR Pages proof, run `35438579639` attempt 1, is **PASS**, and the surrounding named technical lanes are green, but this is branch-only evidence: protected maintainer approval is **FAIL** and a substantive advisory review was not established. Review of #336 exposed a separate PR Agent governance defect in which a provider-credit failure could emit only `Failed to review PR` while the old verifier could count that bot comment as a published advisory, and bot issue comments could interfere with legitimate review through shared concurrency. Open **#337** at `46e522b4437d42d68df170285bd3a93366808bd1` makes that gate fail closed by requiring the explicit full-review marker and isolating bot-comment concurrency. #337 remains unmerged with maintainer approval and PR Agent advisory **FAIL**. Do not attest or merge #336 ahead of #337; if #337 lands, #336 must reconcile to the resulting new `main` and requalify on its new exact head. Production remains **FAIL** until a repaired merged-main revision passes its own first authoritative Pages attempt.

Historical failures remain evidence even when later revisions pass.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged provider/session/bootstrap/publication changes, including #260, do not substitute for fresh live semantic evidence. A fresh real-account mission on an accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain open.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

Qualification-v1 is also a separate branch evidence path. **#333** reverse-merged current `main` into `testing/qualification-v1`, moving open PR **#152** to exact head `11c0ac67f60f61a7243bcc79ce803d588a89aa94`. The first exact-head Qualification-v1 run on that revision, `35443955204` attempt 1, is **FAIL**. Retained evidence records three required non-PASS gates: `deterministic-regression`, `qualification-selftests`, and `toxic-provider-matrix`. The deterministic gate had seven enterprise sandbox test failures because the hosted runner reported `kernel-level sandbox isolation unavailable`; the provider-mission qualifier returned `FAIL`, which caused both the selftest and toxic-provider gates to fail. The lower-level provider-mission cause remains **UNKNOWN** from the retained gate evidence. Factory ownership, M4 prerequisites, browser VM, Controller/provider, Command Station, clean-install and several other surrounding lanes are **PASS**, but partial PASSes do not override the overall required-gate **FAIL**. Protected maintainer approval and PR Agent advisory are also **FAIL**. The earlier `24816ebc...` technical PASS remains retained historical evidence for that exact predecessor head only; none of this branch evidence becomes accepted current-main capability.

## Research evidence boundary

Research results are revision-bound and deliberately mixed:

- #220 / M6-SPEC-006 remains a bounded corrected-path self-hosting **PASS**; earlier M6 self-host trials retain **FAIL** evidence.
- #257 / M6-SPEC-007J is a bounded autonomous-discovery **PASS at formal MeasurementGap admission**. Later registry/provenance/planner experiments retain PASS, FAIL and UNKNOWN cells. General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**.
- #207/#212 retain historical accounting/release-ordering and failure-matrix evidence. The accepted #288 repair closes the product defect tracked by #208, but it does not retroactively change those frozen outcomes; affected stronger claims require fresh repaired-path requalification.
- #319 / M6-MESH-001 is one positive bounded two-obligation concurrency pilot; general mesh/swarm efficiency remains **UNKNOWN / not established**.
- Draft #323 Research Workbench remains **BLOCKED for its first authoritative trial** pending rebase and requalification onto a main containing #288.

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

1. Resolve the **#337** PR Agent governance blocker first; then reconcile and requalify **#336** on the resulting exact `main` before any merge. Preserve production run `35437556200` attempt 1 as **FAIL**; production does not become PASS until a repaired merged-main revision passes its own first authoritative Pages attempt.
2. Requalify stronger budget/unknown-usage/release-ordering claims against the accepted #288 repair; historical frozen failures remain visible.
3. Rebase and requalify #323 before any first authoritative Research Workbench trial.
4. Validate the merged #320 policy on the production Vercel origin before calling response-header remediation PASS in production.
5. Diagnose and repair exact-head #152 Qualification-v1 run `35443955204` without hiding its deterministic/provider-mission failures; then rerun only on a changed head and retain exact-head governance/security review.
6. Retain a fresh real-account Puter candidate→verifier→receipt success on an accepted deployed revision, or keep live-provider success `UNKNOWN`.
7. Complete physical mobile fallback validation, true blank-environment installation, recovery/host-loss qualification, selected elapsed soak, and #120/#126 long-run WebVM reliability work without broadening bounded evidence.
8. Keep M6/M7 research bounded: general recursive self-improvement and general mesh efficiency remain `UNKNOWN`; M6-008 remains `BLOCKED`.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, autonomous recursive self-improvement, autonomous merge authority, production Vercel security-header validation, or live proof of the central research hypothesis.