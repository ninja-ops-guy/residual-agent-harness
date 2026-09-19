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

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged **#330** on 2026-09-19.

Accepted changes relevant to the present boundary include #307 CI fan-out repair, #260 provider-bootstrap hardening, #288 pre-dispatch Station budget/deadline admission, #320 repository-side CSP/anti-clickjacking policy, #328 core non-workflow execution/egress/XML security hardening, and **#330 workflow checkout credential hardening**. #330 disables persisted checkout credentials and adds structural regression coverage while preserving the accepted workflow-trigger semantics. It is a scoped CI-security improvement, not blanket production or security qualification. The stale overlapping #324 branch must not be merged wholesale.

Accepted #276 requires each `main` SHA to receive a non-cancelling first production Pages attempt. For exact current main `3bfa6aba...`, run **`35437556200`**, attempt 1, completed **FAIL**. The generated artifact/browser proof, deployment, served-revision identity, and desktop real-guest path passed; the required narrow/mobile Chromium acceptance failed after reaching the live guest and multiple Workbench stages. Retained live-proof artifact `10582812524` has SHA-256 `868ca31506d278a335ff95d3607adbd13c14edaec8b161c1b45ac013e7f7c8b8`. The lower-level cause remains **UNKNOWN**. The previous exact-main run `35431634267`, attempt 1, remains a scoped **PASS for `0a675017...` only** and must not be inherited after main moved.

Open **#336** is the focused changed-head durability repair. At exact head `92aca285a9287b73787b552f87aaa42062e73ba4`, its generated PR Pages proof `35438579639` attempt 1 is **PASS** and surrounding named technical lanes are green, but the evidence is branch-scoped: protected maintainer approval is **FAIL** and a substantive advisory review was not established. Review discovered a fail-open PR Agent publication check and bot-comment concurrency interference. Open **#337** at `46e522b4437d42d68df170285bd3a93366808bd1` requires the explicit full-review marker and isolates the concurrency classes. #337 remains unmerged with PR Agent and maintainer gates **FAIL**. Do not treat #336 as accepted or production-qualified; if #337 changes `main`, #336 must reconcile and requalify on a new exact head, and the resulting merged main must still pass its own first authoritative Pages attempt.

Open **#338** is a separate protected Factory candidate at exact head `61986ecb56e35a845f2a66b64052b42b13e60be3`. It adds bounded `RuntimeJournal.__init__` write-admission retry and advances the Factory ownership baseline pin. Its Factory ownership, Factory runtime/OS, Control Plane, Command Station, Controller/provider, clean-install, measured-evaluation and maintainer-approval lanes are **PASS**; generated PR Pages and PR Agent advisory are **FAIL**. Those results do not authorize acceptance. Because #338 changes protected RuntimeJournal bytes plus the ownership baseline, it requires explicit trust-boundary review and must not be auto-merged.

Open **#340** proposes Moonshot/Kimi and Kimi Claw/OpenClaw provider/runtime adapters. It remains unaccepted branch work; current qualification is incomplete and exact-head maintainer approval is **FAIL**. Adapter implementation or green sibling lanes do not establish current-main live-provider success.

The accepted #288 repair closes product issue #208. Historical #207/#212 stress/failure-matrix outcomes remain retained evidence and are not rewritten by the merge; any stronger budget/unknown-usage/release-ordering claim needs fresh qualification on the repaired revision.

The accepted #320 policy is repository configuration; production Vercel response-header acceptance remains **UNKNOWN / pending**.

Historical failures remain retained evidence rather than being erased by later PASS results.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Accepted provider/session/bootstrap/publication changes do not constitute retained proof of successful paid/live Puter inference. A fresh exact-deployed-revision real-account mission must reach normal candidate/verifier/receipt handling before live-provider success becomes `PASS`.

The #186 fallback remains accepted: detected iOS/iPadOS WebKit is routed to the lightweight walkthrough before heavyweight guest boot. Physical heavyweight-WebVM reliability and the lower-level process-kill cause remain **UNKNOWN / unqualified**. Issues #120/#126 remain open.

## Factory and trust-boundary constraints

M2/M3/M4 are implemented and `implementation-status.yaml` remains an implementation-presence manifest. M4 qualification is exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

Accepted #185/#187 protected changes retain their reviewed scope. Keep them distinct from the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence. A green hosted lane does not establish every-host qualification.

Qualification-v1 remains independent testing-branch evidence. Merged **#339** moved open #152 to exact testing-branch head **`19d3917079ee6f7105e78c88e2aae08d25ce4c13`** by repairing provider-mission export to use the real run-control authority path. Exact-head Qualification-v1 run **`35446710781` attempt 1 is FAIL**, but the previous provider-mission-related failures have cleared on this changed revision: `qualification-selftests` is **PASS** and the toxic-provider job is **PASS**. The required deterministic job remains **FAIL** at the full deterministic regression gate. #339 deliberately did not weaken the fail-closed sandbox requirement; the predecessor `11c0ac67...` run `35443955204` remains retained historical FAIL evidence, including the hosted-runner `kernel-level sandbox isolation unavailable` observation and provider-mission failures. Protected maintainer approval and PR Agent advisory remain **FAIL** for #152. The earlier `24816ebc...` positive technical evidence is also historical and exact-head bound only.

This documentation does not alter Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research boundary

Recent research evidence remains mixed:

- #220: bounded corrected M6-SPEC-006 self-hosting **PASS**; earlier M6 self-host trials retain **FAIL** evidence.
- #257: bounded formal MeasurementGap-admission **PASS**; later registry/provenance/planner work includes PASS, FAIL and UNKNOWN cells. General autonomous discovery remains **UNKNOWN / not established**.
- #207/#212: frozen stress/failure-matrix evidence includes accounting/release-ordering and missing-usage failures. #288 repairs the tracked product defect (#208), but those cells remain historical and require repaired-path requalification for stronger claims.
- #319: one bounded concurrency pilot is positive, while general mesh/swarm efficiency remains **UNKNOWN / not established**.
- #323: Research Workbench remains draft and its first authoritative trial remains **BLOCKED** pending rebase/requalification onto a main containing #288.
- M6-008 and broader recursive self-improvement remain **BLOCKED/UNKNOWN** until their specific positive gates are satisfied.

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