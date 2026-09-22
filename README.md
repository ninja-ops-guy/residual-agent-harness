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
- **Qualification v1:** exact-revision evidence envelopes and fail-closed aggregation across deterministic/stateful/history/fault/mutation/coverage, M4, exact-wheel/container and browser qualification gates, plus retained failure-ledger semantics and deeper discovery/soak runners.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main

Current `main` is **`91d32fd8b713c68c1cd2e473013c9e1c33b93572`**.

The release-qualification framework and its focused runner/product-path repairs previously converged through **#152**, **#355**, and **#356**. **#397** is now also accepted main state: its focused WebVM durability repair was merged after exact-head maintainer attestation, producing `main@91d32fd8...`.

The resulting exact-main push evidence includes **RESIDUAL Qualification v1 PASS**, **Deploy GitHub Pages PASS**, **Controller and provider contracts PASS**, **Command Station checks PASS**, **clean-install qualification PASS**, and **M4 qualification runner prerequisites PASS**. Vercel is also **PASS**. The prior `main@b571b91...` Pages failure remains retained historical evidence; it is not rewritten, but the first authoritative Pages run on the repaired `main@91d32fd8...` passed.

Treat these as exact-revision results only. They do **not** establish blanket production readiness, universal/every-host qualification, elapsed 24h/72h/30d soak evidence, live-provider model quality, physical-device reliability, or closure of separate security/release blockers.

Historical failures remain retained evidence even when later revisions pass.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded build-output path, #183 repaired provider-session lifecycle behavior, #189 repaired the provider-helper publication boundary, #205 restored the provider channel across Mission Control reload/remount, and #397 repaired the standalone workbench durability boundary observed in hosted post-deploy acceptance. None of those changes, by itself, is retained proof of successful paid/live Puter inference. A fresh real-account mission on the accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain separate.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

The Qualification-v1 convergence includes an owner-authorized protected ownership-baseline advance for the #152 portability change: platform-neutral `residual/factory/m4_protocol.py` is part of the protected core set, with the ownership baseline recording that pin alongside the previously authorized RuntimeJournal pin. That accepted trust-boundary change remains scoped to its reviewed bytes and evidence. It does not turn unrelated or unavailable-host M4 claims into PASS.

This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research evidence boundary

Research results are revision-bound and deliberately mixed. Historical FAIL/BLOCKED observations remain evidence even when later candidate revisions pass. In particular, automated SLM-00 Lane G/G2 evidence remains exact-candidate research evidence and does not itself authorize a freeze, training, or merge. The current research program remains **NOT FROZEN / UNACCEPTED / NO-TRAINING** until its explicit human authority gates close.

Draft research PR **#401** is an append-only AX-21/SLM-00 evidence check-in on a research branch. It records additional research observations, including G2 remediation and claim narrowing, but explicitly does **not** authorize training, freeze SLM-00, close AUD-1, or advance release status.

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

1. **AUD-1 security convergence (#353) remains the P0 release blocker.** Focused candidate **#399** implements proposed F1/F2/F3/F4/F6 repairs and the ten-adversarial-regression surface, but it remains **UNACCEPTED / NOT MERGE-READY**. The prior exact head `fb416efe29d245fcbbb03f6f8edb8c89a8212f3d` had green technical CI, but PR-Agent correctly identified that adversarial requirement #6 lacked an explicit positive coordinator-transition regression; those results remain exact-head PASS evidence but are superseded for final acceptance. Current exact head **`8df77b832b3839ccd2a6944a65760ce3ab10dc9c`** adds that missing coordinator-vs-worker regression. Fresh exact-head Qualification v1, Pages/browser proof, Factory ownership, Command Station, clean install, measured-evaluation binding, Controller/provider contracts, Control Plane, PR-Agent, and Vercel are **PASS**. Exact-head maintainer approval remains **FAIL** by design because no matching human attestation has been supplied yet. The owner now classifies the **software gate as ready for physical P1 dogfood**, not as release acceptance.
2. #399 still requires the two separately retained physical P1 F6 cases on the real LEGION / DELL7320 / DBOX topology: reconnect inside the retry/authority window and reconnect outside it after authority expiry/reassignment. Those claims remain **UNKNOWN / not established** until distinct retained artifacts exist.
3. After both physical artifacts exist for the exact candidate, retain the standing Mason/LEGION independent read-only re-audit of F1/F2/F3/F4/F6, then satisfy the owner-defined exact-head qualification/attestation sequence before merge and authoritative new-main qualification. Current hosted Qualification-v1 PASS does not authorize skipping the physical or independent-audit gates; any candidate-byte change invalidates affected qualification/audit evidence.
4. Retain a fresh real-account Puter candidate→verifier→receipt success on the accepted deployed revision, or keep live-provider success `UNKNOWN`.
5. Physically validate the #186 mobile fallback without broadening it into a heavyweight-WebVM reliability claim.
6. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak for the exact release artifact; the existence of soak runners is not elapsed-time evidence.
7. Keep SLM-00 research freeze/training authority separate from repository qualification; automated research PASS does not authorize the human freeze.
8. Continue #120/#126 long-run WebVM reliability work and preserve historical FAIL/BLOCKED evidence rather than rewriting it after later fixes.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, closed AUD-1 security convergence, autonomous recursive self-improvement, autonomous merge authority, or live proof of the central research hypothesis.
