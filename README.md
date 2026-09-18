# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI. Merged #194 keeps completed generated-spec drafts visible and reopenable.
- **Mission Control / WebVM:** browser-facing real-guest workflows, provider transport, fail-closed runtime handling, fresh-overlay recovery, privacy-safe diagnostics, an iOS/WebKit pre-boot walkthrough fallback, and WebVM runtime discriminators.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence, observability/economics tooling and bounded adversarial authority testing.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main

Current `main` is **`699e2869e294fe157b4bfd73a272057683a2f7e0`**, produced by merged **#193** after merged documentation PR **#192**.

The important accepted state still includes the material changes that landed before #192:

- **#188** — AQ-GOV-001, a bounded adversarial lab that assumes unanimous worker approval of authority escalation and checks existing quarantine/WorkerContract/AttemptGuard boundaries. It does **not** prove kernel/container/hypervisor/broker escape resistance.
- **#194** — Command Station retains and reopens completed generated specification drafts.
- **#133** — WebVM runtime discriminator tooling. Retained evidence narrows one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`. The exact lower-level CPython/i386 ABI/emulation cause remains **UNKNOWN**.
- **#193** — a one-command interactive native setup helper (`setup.sh`) that creates/reuses a Python 3.11+ venv, installs the checkout, exports its bin directory to PATH, optionally installs a no-argument `residual` serve macro, and prints/opens the local Station URL.

### Documentation correction after #192

PR #192 merged documentation that was based on the earlier `main@dcf1e507...` state and therefore reintroduced stale current-state prose after #188/#194/#133 had already landed. This corrective documentation work restores those accepted facts and adds #193. The documentation regression does not change the underlying implementation/evidence history.

### #133 / #132 scope caveat

Merged #133 also removed the previously accepted #132 protected self-hosting/research-bundle implementation, workflow, tests, example and dedicated research docs. Earlier #133 review records identified those deletions as an integration blocker for a diagnostic-only PR. Because the bytes are absent from current main, #132 remains **historical retained evidence, not current accepted capability**. Whether the removal was intended retirement or an integration regression remains **UNKNOWN / unresolved**.

## Qualification boundary

Before #192/#193, all seven ordinary first-attempt `push` workflows on exact `main@b3f00af29c7507f4c0e218884e491c2fc792d984` completed **PASS**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, Command Station and Pages/deployment.

PR #193's exact candidate head `d97104958a235d9439fd3c36cc72221ba454b3cc` completed the observed exact-head Control Plane, Factory ownership, clean-install, Controller/provider, measured-binding, Command Station and maintainer-approval workflows **PASS** before merge.

Post-merge qualification on exact `main@699e286...` is a separate evidence set. Until its applicable workflows finish, that state is **PENDING**, not inherited from the predecessor or candidate head.

These results do not establish capable-runner/every-host M4 qualification, paid/live provider success, physical heavyweight-WebVM iPhone reliability, blank-environment release qualification, host-loss recovery, elapsed soak, or the central research hypothesis.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded build-output path, #183 repaired provider-session lifecycle behavior, and #189 repaired the provider-helper COI/CORP publication boundary. None, by itself, is retained proof of successful paid/live Puter inference.

Issues **#120** and **#126** remain open. #133 materially improves diagnosis of the CPython timed-wait symptom, but production WebVM long-run reliability and the exact lower-level defect remain **UNKNOWN**.

The accepted #186 fallback routes detected iOS/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. That is not a PASS claim for heavyweight WebVM on physical iPhone Safari.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted protected changes from #185 and #187 remain scoped to their reviewed bytes. The separate **#139 → ownership-baseline decision → fresh qualification → #134** sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes or evidence schemas.

## Governance boundary

Merged **#168** establishes the repository's solo-maintainer control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

Describe that as **maintainer-reviewed with automated qualification**. It is not independent human assurance. Claim-specific independent or third-party evidence remains required wherever a security, release or research claim depends on it.

PR #191 was closed unmerged and is not accepted repository governance.

## Quick start

### Interactive native setup

On a Bash-capable host with Python 3.11+:

```bash
bash setup.sh
```

See [`START-HERE.md`](START-HERE.md) for exact behavior, defaults and security notes. This convenience path is not a blank-environment release qualification result.

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

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

## Current priority gates

1. Finish and retain the exact-current-main post-#193 workflow/deployment set; do not inherit predecessor qualification.
2. Decide whether #133's removal of accepted #132 self-hosting/research-bundle tooling is intentional retirement or an integration regression.
3. Continue #120/#126 WebVM reliability work without promoting the narrowed diagnosis into root-cause proof.
4. Refresh/requalify stale candidates including #190, #152 and #177 before current claims use them.
5. Retain a fresh real-account Puter mission before claiming live-provider PASS, and physically validate the #186 mobile fallback without broadening it into heavyweight-WebVM reliability.
6. Complete true blank-environment install, recovery/host-loss qualification and selected elapsed soak for the exact release artifact.
7. Keep the separate #139→ownership-baseline→#134 protected sequence intact.
8. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5, degradation and heterogeneous-routing studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, root cause of the historical browser-runtime corruption family, autonomous merge authority, current accepted #132 self-maintenance/research-bundle capability, final IE-001 qualification, or live proof of the central research hypothesis.
