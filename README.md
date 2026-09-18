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

Current `main` is **`dcf1e5071deb624c637aa72df575089435d72ac9`**, created by merged **#189** on top of merged **#187**.

Since the prior release-stabilization merge #185:

- **#187** accepted the focused protected M4 safety-test repair for the `/proc/<pid>/status` exit-observation race and deliberately advanced the corresponding Factory ownership-baseline pin. It changes test observation semantics only; it does not establish a runtime termination defect or universal M4 qualification.
- **#189** accepted a Pages/WebVM isolation-boundary fix that keeps the optional `/provider/` helper outside COOP/COEP response rewriting while leaving `/demo/` and the heavyweight WebVM isolation boundary unchanged.

PR #187 exact-head automated qualification and maintainer approval were PASS before merge. PR #189 exact-head Factory ownership, clean install, measured binding, Control Plane, Controller/provider, Command Station, Browser VM Demo, Pages and maintainer approval were PASS before merge.

### Current-main qualification boundary

The first exact-current-main push set on `main@dcf1e507...` completed **PASS on attempt 1** for Factory ownership (`35279264442`), measured-evaluation binding (`35279264666`), M4 runner prerequisites (`35279264635`), clean install (`35279264767`), Controller/provider (`35279264540`), Command Station (`35279264513`), and Pages/deployment (`35279264564`). This establishes the exact merged revision's automated CI/deployment boundary for those workflows.

Historical retained failures remain evidence. In particular, Controller/provider run `35263782697` on `main@e996b585...` remains **FAIL** in Python 3.13. #187 diagnoses and repairs that protected-test observation race, but the historical failure is not erased.

These engineering/browser results do not establish capable-runner/every-host M4 qualification, paid/live provider success, physical heavy-WebVM iPhone reliability, blank-environment release qualification, host-loss recovery, elapsed soak, or the central research hypothesis.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 raised the browser build-only provider-output ceiling/default to 8192 tokens while preserving the 1536-token non-build/source-grounded bound and fail-closed truncation handling. Merged #183 repaired a bounded provider-session lifecycle case. Merged #189 repairs the provider helper's COI/CORP publication boundary. None of those changes, by itself, is retained proof of successful paid/live Puter inference.

The exact-current-main Pages/deployment workflow is PASS, but manual production provider-helper SDK/sign-in behavior and successful paid/live inference remain **UNKNOWN** until retained production evidence exists. A fresh real-account mission must cross provider protocol validation into normal candidate/verifier/receipt handling before live-provider success can become PASS.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. Dedicated preflight coverage is not proof that heavyweight WebVM is reliable on physical iPhone Safari; physical-device validation and the lower-level WebKit crash cause remain open/UNKNOWN.

Issues **#120** and **#126** remain open. Historical timed-wait/runtime-corruption evidence, poisoned-guest behavior, and physical iPhone/WebKit failure do not yet establish a shared root cause or acceptable long-run recurrence rate.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

The #185 protected runtime-journal bytes and ownership-baseline update remain accepted. #187 additionally accepts the protected test-only `/proc` race repair and its ownership pin. Those accepted bytes do **not** clear unrelated protected work or turn hosted/prerequisite CI into universal capable-runner M4 qualification.

PR **#139** and downstream **#134** remain a separate protected-byte sequence and must be re-evaluated against current main rather than inferred cleared by #187.

This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, or evidence schemas.

## Governance boundary

Merged **#168** establishes the repository's solo-maintainer control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

Describe that as **maintainer-reviewed with automated qualification**. It is not independent human assurance. Claim-specific independent or third-party evidence remains required wherever a security, release or research claim depends on it.

PR #191, which proposed an automated PR Agent workflow, was closed unmerged and is not part of accepted repository governance.

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

Update an existing installation with `residual update`. Source checkouts are
updated only by clean fast-forward to their configured upstream; package installs
use the current Python interpreter's pip. Preview the selected path with
`residual update --dry-run`.

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

## Current priority gates

1. Verify the production provider helper on the deployed current-main revision; SDK load/sign-in availability remains UNKNOWN until retained manual production evidence exists.
2. Complete #190 exact-head qualification/maintainer governance on its refreshed current-main head before integration; if accepted, retest provider-session recovery on the deployed revision.
3. Retain a fresh real-account Puter build before claiming live-provider PASS, or explicitly exclude that claim.
4. Physically validate the accepted #186 mobile fallback without broadening it into a heavy-WebVM reliability claim.
5. Complete true blank-environment install, recovery/host-loss qualification, and selected elapsed soak for the exact release artifact.
6. Continue #120/#126 long-run WebVM reliability work and the separate #139→ownership-baseline→#134 protected sequence.
7. Refresh/requalify broader Qualification v1 work (#152) and IE-001 candidate #177 before current claims use them.
8. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5, degradation and heterogeneous-routing studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, verified production provider-helper sign-in behavior, physical heavy-WebVM iPhone reliability, root cause of the historical browser-runtime corruption family, autonomous merge authority, final IE-001 qualification, or live proof of the central research hypothesis.
