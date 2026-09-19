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

Current `main` is **`d89c5d940a32d8a7df4dd55e699c158fff5f615c`**, produced by merged **#336** on 2026-09-19 after **#337** landed the PR-Agent advisory-governance repair.

Accepted #337 requires substantive PR-Agent full-review evidence rather than treating a bot status/failure comment as advisory publication, and separates status/review concurrency. Accepted #336 adds a guest-filesystem durability boundary before Mission Control/WebVM publishes reusable worker completion. Both changes are scoped; neither broadens Factory/M4, verifier, evidence-schema, provider, or acceptance authority.

Accepted #276 requires each `main` SHA to receive a non-cancelling first production Pages attempt. Exact-current-main run **`35449637725`**, attempt 1, is **FAIL**. Generated desktop+narrow proof, deployment, published desktop exact-revision/real-guest execution, and several narrow live-guest stages passed. The required narrow path later failed a compound retained-evidence assertion that checks the live/build/follow-up artifacts and then runs `verify_run(...)` over all three mission directories. Because those predicates were chained, the retained run does not identify the first failing subpredicate. The lower-level cause remains **UNKNOWN**.

Retained artifact: `webvm-live-proof-35449637725-1`; SHA-256 `edd0d84e1270b71cc53039cae85e42041c06767c52039bb6c418a3ffffd62ff8`. The #336 `os.sync()` boundary is therefore **necessary but insufficient** for full narrow reload/evidence acceptance. The next changed-head repair should split the compound assertion into independently reported existence and `verify_run(...)` checks without weakening either. The unchanged current head must not be rerun merely to obtain green.

Historical production Pages results remain revision-bound evidence: `0a675017...` run `35431634267` attempt 1 is a scoped **PASS** for that exact revision only; `3bfa6aba...` and `e7b72ad...` retain their exact-revision **FAIL** results.

Open **#338** remains a protected Factory candidate. It changes `RuntimeJournal` protected bytes and the Factory ownership baseline and is rebased onto current main. Regardless of sibling green lanes, it requires explicit trust-boundary review and must not be auto-merged.

Open **#340** is implementation-only provider/runtime adapter work for Moonshot/Kimi and Kimi Claw/OpenClaw. Draft **#341** contains the separated `EXP-NESTED-SWARM-001` research/evaluation track and is explicitly research-only. Neither is accepted current-main capability or live-provider evidence.

The accepted #288 repair closes product issue #208. Historical #207/#212 stress/failure-matrix outcomes remain retained evidence and are not rewritten by the merge; stronger budget/unknown-usage/release-ordering claims need fresh qualification on the repaired revision.

The accepted #320 policy is repository configuration; production Vercel response-header acceptance remains **UNKNOWN / pending**.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Accepted provider/session/bootstrap/publication changes do not constitute retained proof of successful paid/live Puter inference. A fresh exact-deployed-revision real-account mission must reach normal candidate/verifier/receipt handling before live-provider success becomes `PASS`.

The #186 fallback remains accepted: detected iOS/iPadOS WebKit is routed to the lightweight walkthrough before heavyweight guest boot. Physical heavyweight-WebVM reliability and the lower-level process-kill cause remain **UNKNOWN / unqualified**. Issues #120/#126 remain open.

## Factory and trust-boundary constraints

M2/M3/M4 are implemented and `implementation-status.yaml` remains an implementation-presence manifest. M4 qualification is exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

Accepted #185/#187 protected changes retain their reviewed scope. Keep them distinct from the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence. A green hosted lane does not establish every-host qualification.

Qualification-v1 remains independent testing-branch evidence. Open **#152** is now at exact head **`aeba9962918c3659693e1efcd5603275cfb77cb4`**. Exact-head run **`35448856959` attempt 1 is FAIL**. Real bubblewrap provisioning passed and the visible sibling jobs including self-tests, toxic-provider, M4, browser, discovery, concurrency and fault injection passed, but the required deterministic job failed at `Full deterministic regression gate`; the aggregate therefore failed closed. The retained summary does not establish a more specific lower-level cause. #152 remains unaccepted and its governance gates are unsatisfied. Earlier branch results remain historical exact-head evidence only.

This documentation does not alter Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, or evidence schemas.

## Research boundary

Recent research evidence remains mixed:

- #220: bounded corrected M6-SPEC-006 self-hosting **PASS**; earlier M6 self-host trials retain **FAIL** evidence.
- #257: bounded formal MeasurementGap-admission **PASS**; later registry/provenance/planner work includes PASS, FAIL and UNKNOWN cells. General autonomous discovery remains **UNKNOWN / not established**.
- #207/#212: frozen stress/failure-matrix evidence includes accounting/release-ordering and missing-usage failures. #288 repairs the tracked product defect (#208), but those cells remain historical and require repaired-path requalification for stronger claims.
- #319: one bounded concurrency pilot is positive, while general mesh/swarm efficiency remains **UNKNOWN / not established**.
- #323: Research Workbench remains draft and its first authoritative trial remains **BLOCKED** pending rebase/requalification onto a main containing #288.
- #341: governed nested-runtime evaluation is draft research-only work, not evidence of general nested-swarm benefit.
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