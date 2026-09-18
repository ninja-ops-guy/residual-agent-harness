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

### How the pieces fit

```mermaid
flowchart LR
  U["Operator"] --> C["Core harness<br/>obligations + host verifier"]
  U --> S["Command Station<br/>queue + checks + review + integration"]
  U --> M["Mission Control<br/>browser / WebVM"]
  C --> P["Configured model providers"]
  S --> P
  M --> B["Session-scoped provider bridge"] --> PP["Puter / external provider boundary"]
  S -. bounded Factory work .-> F["Factory M2 → M3 → M4"]
  C --> E["Receipts / retained evidence"]
  S --> E
  F --> E
  E -. observed by .-> R["Evaluation / research"]
```

The surfaces share evidence-first authority rules, but they are not one mandatory linear pipeline. Provider/model output is a proposal; host-owned verification and integration boundaries determine accepted state.

## Current main

Current `main` is **`3cff6bcd52e352a6ba048c958949a7bbb2a039eb`**, produced by merged PR **#197** on top of #248.

Accepted changes in the current documented sequence include:

- **#200** — native setup hardening. The setup path defaults to persistent XDG state, binds Station to `127.0.0.1`, makes the convenience shell macro opt-in, uses bounded venv repair, and constrains shell startup-file edits. This is onboarding hardening, **not** blank-environment qualification or a portability proof.
- **#205** — WebVM provider-channel recovery. Mission Control restores the private provider channel token from `sessionStorage` across reload/remount, validates it fail-closed, reuses it only for the active browser session, and clears it on explicit close. This is accepted provider-session lifecycle behavior, **not** retained proof of live Puter inference.
- **#218** — bounded Station repair-loop remediation. Repair attempts may receive the previous failed candidate's declared writable files as bounded context while each new attempt still starts from a clean baseline worktree; repair-context hashes are retained, the runner contract separates the transport JSON envelope from file-language content, and Mission Control/Store share a bounded five-attempt ceiling. This does **not** weaken verifier, review, receipt, integration, quarantine, promotion, Factory/M4, or acceptance authority.
- **#201** — frontend/guided-provider UX. The public site separates guided proof from the interactive WebVM lab, animates real RESIDUAL CLI commands with reduced-motion support, and Mission Control keeps Puter setup inline while allowing Puter's secure authorization popup under explicit user gesture. Provider loading remains lazy, credentials stay outside RESIDUAL, and protocol handling remains fail-closed.
- **#233** — Station repair diagnostics. Failed attempts retain an actionable failure tail and repeated failed patches are detected explicitly so a repair loop does not silently lose the root cause or treat an identical failed patch as progress. The change does not grant worker, review, receipt, integration, promotion, verifier, or Factory/M4 authority.
- **#248** — provider-load lifecycle qualification repair. The embedded provider path tracks a monotonically increasing load generation and explicit `requested → loading → failed|loaded` state, binds activation to the intended credentialless frame, and retains assertions that a credentialless load attempt actually occurs and the intentionally blocked network path fails closed. This is accepted lifecycle/test behavior, **not** evidence of successful real Puter authentication or paid/live inference.
- **#197** — PR-review governance hardening. It changes advisory review workflow/configuration only. It does not modify runtime, provider, Factory/M4, verifier, evidence-schema, or acceptance behavior.

Exact current `main@3cff6bcd...` has six successful ordinary push workflows in their named scopes. The most recent retained **production Pages acceptance** remains the first attempt on its parent `main@de7d9774...`, run `35363306307`, and remains **FAIL**. That run's generated desktop+narrow artifact proof and deployment passed; published desktop acceptance later timed out because `#signin` remained disabled during the guided provider sequence.

Retained proof for that production failure records `cloud_inference: NOT_RUN`, provider evidence `REAL_GUEST_WITH_TEST_DOUBLE_SDK_NOT_PAID_INFERENCE`, and authorization evidence `USER_GESTURE_AND_POPUP_CONTRACT_TEST_DOUBLE_NOT_REAL_PUTER_LOGIN`. The trace supports a repository/UI bootstrap race, not a Puter outage, real authentication failure, model-quality failure, or paid/live inference result.

Historical failures remain evidence even when later revisions or PR heads pass.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary; candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179, #183, #189, #205, #201 and #248 repair or improve bounded build-output, provider-session, publication, reload-recovery, guided setup and provider-load lifecycle surfaces. None is retained proof of successful paid/live Puter inference. A fresh real-account mission on the accepted deployed revision must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling before live-provider success can become `PASS`.

PR **#253** is closed unmerged and historical. Its current-main replacement, open **#260**, is rebuilt directly on exact `main@3cff6bcd...`. #260's exact head has all applicable technical workflows **PASS**, including Browser VM Demo CI and Deploy GitHub Pages; the exact-head maintainer approval gate remains **FAIL / pending matching attestation**. Those PR-head results do not replace the retained production Pages FAIL. If #260 is accepted, the resulting merged-main SHA requires its own first published Pages acceptance attempt.

The accepted #186 fallback routes detected iPhone/iPadOS WebKit to the lightweight walkthrough before heavyweight WebVM boot. This is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain open.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research evidence boundary

Research results are revision-bound and deliberately mixed:

- Draft #202 retains an earlier heterogeneous-DAG **FAIL** and a later distinct exact-head bounded **PASS** using real local models for a three-task DAG with forced repair. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.
- Draft #203/#204 and #215/#217 remain retained M6 **FAIL** results.
- Draft #220 M6-SPEC-006 remains a bounded **PASS** on the corrected #218 runtime using local Qwen2.5-Coder 7B. It does not establish general autonomous self-maintenance.
- **#231 / M6-ROADMAP-001B** is a research **PASS** against a detached clean copy of exact `main@260b5f9...`: one implementation attempt, 3/3 immutable checks PASS, independent local review APPROVED, exact reviewed head integrated, a verification receipt was issued, and release export succeeded.
- Production **#243** remains open/unaccepted. It imports the generated #231 implementation but includes maintainer deep-immutability hardening, so its current bytes are not claimed to be exactly RESIDUAL-generated. Its applicable technical workflows are **PASS** while the exact-head maintainer approval gate is still **FAIL / pending matching attestation**.
- **#232 / M6-EPI-001** completed its two-arm research experiment successfully while exposing deterministic HypothesisVerifier rejection requirements. That is a research finding, not proof that the production HypothesisVerifier exists or is qualified.
- **#244 / #246** failed before discovery because the local provider timed out. **#249** reached discovery but malformed/repeated/truncated output exhausted its bounded repair budget. **#250/#251/#252/#254** eliminated the malformed-JSON class with typed output but still **FAILed** deterministic admission because the Scientist called already-measured metrics missing.
- **#255 / M6-SPEC-007H** reached semantic review with a genuinely absent-metric-shaped MeasurementGap, but review rejected causal overclaim, non-falsifiable acceptance, and preservation-criteria defects: bounded **FAIL**, no admission receipt.
- **#256 / 007I** and **#258 / 007K** are **FAIL in experiment-execution/apparatus scope** (stale task-ID and pre-model variable-name defects respectively); they are not evidence against the Scientist hypothesis.
- **#257 / M6-SPEC-007J** is the first retained bounded autonomous-discovery **PASS at formal admission** in this sequence: local `qwen2.5:7b` produced a MeasurementGap for genuinely absent `context_bytes_non_success_max`; semantic review approved it and a verification/admission receipt was issued. This establishes one bounded admission path only, not general autonomous discovery.
- **#259 / 007L**, **#262 / 007M**, and **#263 / 007N** remain bounded **FAILs** after closing the admitted gap and adding host evidence resolution/active evidence selection. The host correctly exposed or resolved present metrics, but the Scientist continued requesting metrics already present and ultimately repeated already-resolved evidence requests. No later admission receipt was issued.
- Draft #207 campaign B retains negative governance evidence: budget/release authority-ordering defects remain open until an accepted repair is requalified.

The correct aggregate claim remains: one bounded autonomous MeasurementGap admission has now **PASSed**, while repeated follow-up cells still fail evidence use/repair. General autonomous improvement discovery and recursive self-improvement remain **UNKNOWN / not established**.

See [`docs/research.md`](docs/research.md) and [`docs/evaluation.md`](docs/evaluation.md).

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

1. Preserve production Pages run `35363306307` as retained authoritative **FAIL** for `main@de7d9774...`. Review/attest #260 on its exact head if appropriate; if accepted, require the resulting merged main's first published Pages acceptance attempt rather than treating PR-head Pages PASS as production proof.
2. Review and qualify production PR #243 before calling `ImprovementSpec` accepted main behavior. Its technical PR-head workflows are green, but its current head includes maintainer hardening beyond the exact #231-generated bytes and still lacks exact-head maintainer approval.
3. Preserve #257/007J as a bounded admission **PASS**, while treating #259/#262/#263 as retained negative evidence that evidence resolution alone has not yet taught the Scientist to use resolved measurements coherently. General autonomous discovery remains `UNKNOWN`.
4. Continue the remaining M6.2 contracts — EvidenceSnapshot, MeasurementGap, Scientist, deterministic HypothesisVerifier, experiment ledger, and champion/challenger evaluation — without weakening external verification authority.
5. Repair and requalify the #207/#208/#212 accounting/release-ordering defects before making stronger fail-closed budget/release claims.
6. Retain a fresh real-account Puter candidate→verifier→receipt success on an accepted deployed revision, or keep live-provider success `UNKNOWN`.
7. Physically validate the #186 mobile fallback without broadening it into a heavyweight-WebVM reliability claim.
8. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak for the exact release artifact.
9. Continue #120/#126 long-run WebVM reliability work and the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence.
10. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5 and the planned degradation/routing studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, general autonomous recursive self-improvement, autonomous merge authority, or live proof of the central research hypothesis.