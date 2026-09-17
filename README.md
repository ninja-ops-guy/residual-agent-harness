# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution, fail-closed runtime handling, fresh-overlay poisoned-guest recovery, privacy-safe diagnostics, and an iOS/WebKit pre-boot walkthrough fallback.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence, observability/economics tooling, AQ-GOV-001 authority-escalation testing, and WebVM runtime diagnostics.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main

Current `main` is **`b3f00af29c7507f4c0e218884e491c2fc792d984`**. Since the previously documented `main@dcf1e507...`, three material merges landed:

- **#188** — AQ-GOV-001, an additive adversarial lab that assumes 10/10 workers approve authority escalation and checks existing quarantine/WorkerContract/AttemptGuard boundaries. It is now accepted test/research apparatus, but it does **not** prove kernel/container/hypervisor/broker escape resistance.
- **#194** — Command Station now retains the latest completed generated specification draft, exposes it as a clickable completed job, and can repopulate Mission Intake after the original in-memory watcher is gone.
- **#133** — WebVM runtime diagnostic tooling/workflows were merged. Retained diagnostics narrow one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`. Direct libc wait controls continue beyond the same boundary. The lower-level CPython/i386 ABI/emulation cause remains **UNKNOWN**, as does its relationship to the older corruption family.

### #133 scope caveat

The merged #133 diff also removed the previously accepted #132 protected self-hosting/research-bundle implementation, workflow, tests, example, and dedicated research docs. Earlier review records explicitly identified those deletions as an integration blocker for a supposedly diagnostic-only PR. Because the bytes are now absent from current main, bounded self-maintenance/research-bundle tooling is **historical #132 evidence, not current accepted capability**. This documentation does not infer whether that removal was the intended retirement decision; that disposition remains an explicit follow-up.

### Current-main qualification boundary

The first seven ordinary `push` workflows for exact `main@b3f00af...` were **queued/pending** at the latest observation. No PASS is inherited from predecessor main or from #133's candidate head.

On #133's exact final candidate head, the ordinary Factory ownership, measured-binding, Browser VM Demo, Control Plane, clean-install, Command Station, Controller/provider, Pages, and maintainer-approval workflows completed **PASS**. Multiple WebVM discriminator workflows intentionally completed **FAIL** because they successfully reproduced the runtime defect under test; those retained diagnostic failures are evidence, not failures to rerun away.

Historical exact-main PASS/FAIL evidence remains bound to the revisions that produced it. These results do not establish capable-runner/every-host M4 qualification, paid/live provider success, physical heavyweight-WebVM iPhone reliability, blank-environment release qualification, host-loss recovery, elapsed soak, or the central research hypothesis.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded build-output path; #183 repaired a provider-session lifecycle case; #189 repaired the provider-helper COI/CORP publication boundary. None, by itself, is retained proof of successful paid/live Puter inference.

Issues **#120** and **#126** remain open. #133 materially improves diagnosis of the CPython timed-wait symptom, but production WebVM long-run reliability and the exact lower-level defect remain **UNKNOWN**.

The accepted #186 fallback routes detected iOS/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. That is not a PASS claim for heavyweight WebVM on physical iPhone Safari.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted protected changes from #185 and #187 remain scoped to their reviewed bytes. The separate **#139 → ownership-baseline decision → fresh qualification → #134** sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, or evidence schemas.

## Governance boundary

Merged **#168** establishes the repository's solo-maintainer control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

Describe that as **maintainer-reviewed with automated qualification**. It is not independent human assurance. Claim-specific independent or third-party evidence remains required wherever a security, release, or research claim depends on it.

PR #191 was closed unmerged and is not accepted repository governance.

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

1. Complete the first exact-current-main workflow/deployment set for `b3f00af...`; preserve any first failure rather than inheriting predecessor PASS.
2. Decide whether #133's removal of accepted #132 self-hosting/research-bundle tooling is intentional retirement or an integration regression; restore/reintroduce only through a focused reviewed change if needed.
3. Continue #120/#126 WebVM reliability work from the #133 evidence without promoting the narrowed diagnosis into root-cause proof.
4. Refresh/requalify stale candidates, including #190, #152, and #177, after the material `main` move before current claims use them.
5. Retain a fresh real-account Puter mission before claiming live-provider PASS, and physically validate the #186 mobile fallback without broadening it into heavyweight-WebVM reliability.
6. Complete true blank-environment install, recovery/host-loss qualification, and selected elapsed soak for the exact release artifact.
7. Keep the separate #139→ownership-baseline→#134 protected sequence intact.
8. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5, degradation, and heterogeneous-routing studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, verified production provider-helper sign-in behavior, physical heavyweight-WebVM iPhone reliability, root cause of the historical browser-runtime corruption family, autonomous merge authority, current accepted #132 self-maintenance/research-bundle capability, final IE-001 qualification, or live proof of the central research hypothesis.
