# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution, fail-closed runtime handling, fresh-overlay poisoned-guest recovery, privacy-safe local diagnostics, and an iOS/WebKit pre-boot walkthrough fallback.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main

Current `main` is **`e996b58566847e88153e6e5196625d52b93e081a`**, created by merged **#185**, the release-stabilization integration.

#185 carries into accepted main:

- the bounded SQLite writer-admission change in protected `residual/factory/runtime_journal.py` plus the corresponding `verifier/v3/factory_ownership_baseline.json` advance;
- the #186 iOS/iPadOS WebKit pre-boot fallback to the lightweight walkthrough;
- the previously accepted #179 browser build-output mitigation and #183 mobile provider-session lifecycle behavior through the inherited main lineage.

The final #185 candidate head `068954dd6c1c9a56c9a18fbbce67b1504e2c4b7d` received exact-head maintainer attestation before merge. Under #168 governance this is **maintainer-reviewed with automated qualification**, not independent human assurance.

### Current-main qualification boundary

Latest observed applicable runs on exact current main are **PASS**, including Factory ownership, clean install, measured-evaluation binding, M4 prerequisites, Controller/provider, Command Station, iOS WebKit preflight, and Pages/deployment.

One earlier **Controller and provider contracts** run on the same SHA, `35263782697`, remains retained **FAIL** in Python 3.13; a later same-SHA run `35264069649` is PASS. The exact cause of the earlier failure is **UNKNOWN** from the retained evidence reviewed here. It must not be erased or described as a code-level fix merely because a later unchanged-SHA run passed.

Current-main **Command Station** run `35264069706` is PASS. The older `main@2e1341c9...` Command Station run `35219212073` remains historical FAIL evidence. **Deploy GitHub Pages** run `35263783090`, attempt 1, is PASS.

These are scoped engineering/browser/deployment results. They do not establish paid/live provider success, physical heavy-WebVM reliability, blank-environment release qualification, host-loss recovery, elapsed soak, or the central research hypothesis.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 raised the browser build-only provider-output ceiling/default to 8192 tokens while preserving the 1536-token non-build/source-grounded bound and fail-closed truncation handling. That is a bounded mitigation, not proof that truncation caused the historical failure. Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until retained real-account evidence crosses provider protocol validation and proceeds through normal candidate/verifier/receipt handling.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. Dedicated current-main WebKit preflight is PASS. This is **not** proof that heavyweight WebVM is reliable on physical iPhone Safari; physical-device validation and the lower-level WebKit crash cause remain open/UNKNOWN.

Issues **#120** and **#126** remain open. Historical timed-wait/runtime-corruption evidence, poisoned-guest behavior, and physical iPhone/WebKit failure do not yet establish a shared root cause or acceptable long-run recurrence rate.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

The #185 protected runtime-journal bytes and ownership-baseline update are now accepted on main, but their acceptance does not clear unrelated historical protected failures. PR **#139** remains the isolated repair lane for the older protected `/proc/<pid>/status` observation race where applicable; downstream **#134** still follows that separate protected-byte/ownership-baseline sequence.

This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, or evidence schemas.

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

See [`START-HERE.md`](START-HERE.md) for installation and operator setup.

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

## Current priority gates

1. Preserve Controller/provider run `35263782697` as retained same-SHA **FAIL** evidence; keep the exact cause **UNKNOWN** unless retained evidence identifies it.
2. Physically validate the accepted #186 mobile fallback after publication without broadening it into a heavy-WebVM reliability claim.
3. Retain a fresh real-account Puter build on the exact deployed accepted revision before claiming live-provider PASS, or explicitly exclude that claim.
4. Complete true blank-environment install, recovery/host-loss qualification, and selected elapsed soak for the exact release artifact.
5. Continue #120/#126 long-run WebVM reliability work and the separate #139→ownership-baseline→#134 protected sequence.
6. Refresh/requalify broader Qualification v1 work (#152) before using it as current release evidence.
7. Reconcile/refresh #177 against the current IE-001 contract/governance before final IE-001 qualification.
8. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5, degradation and heterogeneous-routing studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavy-WebVM iPhone reliability, root cause of the historical browser-runtime corruption family, autonomous merge authority, final IE-001 qualification, or live proof of the central research hypothesis.
