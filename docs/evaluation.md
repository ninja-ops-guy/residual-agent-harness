# Evaluation and reproduction

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

RESIDUAL has two evaluation layers: the original controller benchmark/study path and the frozen reliability-evaluation apparatus under `residual/eval/`. Both are useful, but they answer different questions and must not be mixed into one claim.

## Offline verification

```bash
python3 -m unittest discover -s tests -v
python3 -m residual demo --output runs/demo
python3 -m residual verify-trace runs/demo/trace.jsonl --result runs/demo/result.json
python3 -m residual run examples/incident/task.json --config examples/demo.toml --output runs/incident
```

Transport/contract tests prove the behavior they exercise. They do **not** establish live model quality merely because an adapter or browser workflow is green.

## Original scripted controller experiments

```bash
python3 -m residual benchmark --cases 8 --noise-lines 256 --output docs/benchmark-simulation.json
python3 -m scripts.scale_study
```

The scripted benchmark is useful for deterministic controller/evidence regression. It does not demonstrate that cloud reasoning is necessary, that real models preserve quality, or that simulated request-byte savings predict live billed cost.

Failures, abstentions and missing usage remain in denominators. Missing provider usage remains unknown rather than being reported as zero-cost evidence.

## Frozen reliability evaluation

The research apparatus includes immutable workload definitions, repeated configuration runs, ablations, statistics/comparison reports, fault injection, evidence/report reconstruction and Factory measurement hooks.

Paper-facing metrics include raw candidate correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, Accepted Error Rate, accepted-system success, false acceptance/rejection, verifier rejection/`UNKNOWN`, throughput/latency, orchestration/rework/conflict overhead, and directly measurable monetary/token/GPU cost.

A system that rejects nearly everything must not be described as reliable merely because accepted error is low. Report acceptance coverage alongside accepted correctness.

## Current integration evidence is not confirmatory evidence

Current `main` is **`2f9dda3882f39c28a1c766859b1bf9579eea7911`**, produced by merged #338 after #336/#337 on 2026-09-19. #337 repairs PR-Agent advisory publication/concurrency governance; #336 adds a guest-filesystem durability boundary before reusable WebVM completion; #338 adds bounded contention-only RuntimeJournal constructor admission retry and advances the protected Factory ownership pin. These are engineering/governance changes, not model-quality or scientific evidence.

Accepted #276 requires each `main` SHA to receive its own non-cancelling production Pages attempt. For exact current main, run **`35452581203`**, attempt 1, completed **PASS**. Generated desktop+narrow proof, deployment, published desktop exact-revision/real-guest execution, and published narrow-Chromium verification all passed without rerun.

Retained artifact: `webvm-live-proof-35452581203-1`, SHA-256 `eed4f0722e43af9362eb62bad122de3521e6f391d92b6388b582c92ef1bff63f`.

This is a scoped PASS for the production publication/browser/real-guest acceptance path on exact `2f9dda38...`. It does not establish live model quality, successful paid/live Puter inference, blank-environment install, recovery/host-loss, elapsed soak, physical heavyweight-WebVM reliability, every-host M4 qualification, or a scientific effect size.

Historical production Pages results remain exact-revision evidence. Predecessor `d89c5d94...` run `35449637725` attempt 1 remains **FAIL** at the narrow retained-evidence path, with lower-level cause **UNKNOWN** because its terminal assertion chained multiple artifact-existence and `verify_run(...)` predicates. Earlier `3bfa6aba...`/`e7b72ad...` FAILs and `0a675017...` PASS also remain bound to their own revisions. The current PASS does not erase them.

Merged #338 is protected trust-boundary work, not evaluation evidence. Its exact PR head had a matching maintainer attestation, but the PR-Agent advisory was **FAIL / unavailable** due `credit_balance_exhausted`; no substantive advisory was published. That absence is retained as governance evidence and does not become independent review merely because #338 merged or current Pages is green.

Open #340 contains implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw adapters. Draft #341 contains the separated governed nested-runtime research track and is research-only. Neither may be used as accepted current-main provider or scientific evidence.

## Real-model development evidence must remain mixed

Draft #202 provides a useful example of why first-attempt and revision binding matter. An earlier heterogeneous three-task DAG run remains **FAIL**, while a later distinct exact-head run is a bounded **PASS** with 3/3 integrated, retained receipts, dependency lineage, rejected fault injections, successful repair, and release export using real local Ollama models. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.

The M6 self-host sequence is similarly mixed: #203/#204/#215/#217 retain authoritative **FAIL** cells, while #220/M6-SPEC-006 retains one bounded corrected-path **PASS**. That PASS does not establish general autonomous self-maintenance.

## M6.2 discovery evaluation boundary

Key retained cells include:

- #244/#246: execution **FAIL** before a valid proposal;
- #249: bounded discovery **FAIL** after malformed/repeated/truncated proposals;
- #250/#251/#252/#254: deterministic admission **FAIL** for requests of already-measured evidence;
- #255: semantic-review **FAIL**;
- #257: bounded **PASS at formal MeasurementGap admission**;
- #259/#262/#263: evidence-use/resolver/query **FAIL** cells;
- #264: workflow/receipt integrity succeeded, but scientific conclusion **UNKNOWN** because metric identity/semantics were ambiguous;
- #274: bounded **PASS** for registry/receipt semantic binding;
- #273/#277: provenance/Planner **FAIL** cells, with positive host-owned provenance evidence inside an overall failed trial.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. M6-008 remains **BLOCKED** pending its declared semantic/derivation admission gates.

## Deterministic stress evidence and accepted #288 repair

Draft #207 Campaign B and draft #212 Campaign C retain important frozen outcomes:

- **#207 STRESS-B1 — FAIL:** final token-budget exhaustion was observed after accepted integration/release had already occurred on the frozen baseline.
- **#207 STRESS-B2 — scoped PASS:** the early-convergence control completed without the target trips.
- **#207 STRESS-B3 — FAIL:** terminal verifier failure aborted with 0 integrated, but a non-empty release materialized afterward.
- **#207 STRESS-B4 — containment PASS / recovery FAIL:** injected corrupt candidates were rejected and none integrated, but recovery did not complete within the frozen pass budget.
- **#212 malformed runner / invalid reviewer:** bounded **PASS for fail-closed containment**.
- **#212 reviewer denial then approval:** bounded **PASS for recovery**.
- **#212 transient HTTP 500:** retry/failover success **UNKNOWN / not established**.
- **#212 missing usage:** **FAIL for accounting-before-authority** because a candidate integrated and received a receipt before the later unknown-usage abort.

Merged **#288** closes product issue #208. Historical scenario outcomes remain unchanged. A stronger present-tense claim that the repaired path prevents every affected authority-ordering failure is **UNKNOWN pending fresh repaired-path requalification**.

## Research Workbench and nested-runtime evaluation

Draft #323's first authoritative Workbench trial remains **BLOCKED**. #288 is accepted, but #323 still requires rebase/requalification before an authoritative M6-WB-001 run.

Draft **#341 / EXP-NESTED-SWARM-001** is a governed nested-runtime evaluation track separated from provider implementation #340. Its definitions, adapters, and contracts are apparatus only. General nested-swarm benefit remains **UNKNOWN / not established** until a frozen governed run produces interpretable retained evidence.

## Cooperative mesh evaluation

#319 / M6-MESH-001 Trial 0 is a bounded positive pilot. Both sequential and two-call concurrent conditions passed their six obligation checks; retained means were about 2.1899 s sequential and 1.8300 s concurrent across three repeats on one Ollama host.

That cell supports only the observation made under its frozen conditions. Warm-up/order sensitivity and the small sample mean that statistically durable concurrency benefit and general mesh/swarm efficiency remain **UNKNOWN / not established**.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and proceeds through normal verifier/receipt handling.

Do not substitute green provider-contract, browser, Pages-build, or lifecycle CI for fresh exact-revision provider evidence.

## Security qualification is separate from scientific evaluation

Merged #320, #328, #330, #337, #336 and #338 are accepted configuration/source/workflow/governance/protected-runtime changes in their reviewed scope. Their existence does not turn security or scientific claims into blanket PASS.

- #320 production Vercel response-header enforcement/Aikido revalidation: **UNKNOWN / pending**.
- #328 core source/runtime security split: **accepted** for its reviewed scope.
- #330 checkout credential-persistence hardening: **accepted** for its reviewed workflow scope.
- #337 advisory publication/concurrency hardening: **accepted** for its reviewed governance scope.
- #336 guest evidence-durability boundary: **accepted** as an implementation repair.
- #338 protected RuntimeJournal contention handling + ownership pin: **accepted** for its reviewed scope; exact-head PR-Agent substantive advisory: **FAIL / unavailable**.

Current Vercel build-rate-limit failures do not establish whether the production security headers themselves pass or fail.

## WebVM-dependent evaluation gate

Issues #120/#126/#335 remain relevant. Bounded mitigations, diagnostics, and individual green revisions do not establish an acceptable long-run recurrence rate or a complete root cause.

The #186 fallback is accepted. It establishes only that the unsupported/unqualified iOS WebKit profile is routed to the lightweight walkthrough before heavyweight guest/disk boot. That result must **not** be reported as physical heavyweight-WebVM reliability.

For a confirmatory protocol that depends on WebVM: freeze the exact source/deployed revision, retain exact-revision browser/runtime evidence, preserve first-attempt `FAIL`/`UNKNOWN`, preregister repeated reliability measurement, report operational missingness separately from model correctness, and never describe a safe fallback, transport repair, or one green revision as proof that the broader reliability family is fixed.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

Merged #338 changed protected RuntimeJournal bytes and the Factory ownership baseline under explicit protected-ownership review. Exact-current-main Factory ownership CI is green, but this only validates the pinned current protected tree under that gate; it is not universal M4 qualification.

Qualification-v1 remains a separate testing-branch evidence path. Open PR #152 remains at exact head **`aeba9962918c3659693e1efcd5603275cfb77cb4`**. Exact-head Qualification-v1 run **`35448856959` attempt 1 = FAIL**. Real bubblewrap provisioning passed and the visible selftest, toxic-provider, M4, browser, discovery, concurrency, fault-injection, and lifecycle sibling jobs passed. The required deterministic job failed at `Full deterministic regression gate`; the aggregate failed closed. The retained summary does not establish the lower-level deterministic-regression cause, so it remains **UNKNOWN**.

#152 remains unaccepted and must reconcile/requalify against current main, including #338, before any merge-readiness claim. No testing-branch PASS overrides the required-gate FAIL or becomes accepted current-main Factory/M4 qualification.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and evaluation independence

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. This is **maintainer-reviewed with automated qualification**, not independent human assurance. A failed/missing advisory remains failed/missing even after a merge.

## Live confirmatory evaluation gate

Before paper-facing R0–R5 outcome collection:

1. freeze exact source commit/tree and execution environment;
2. freeze selected evidence/execution adapter and task mapping;
3. freeze workload hashes, model/version, inference settings, and prompts;
4. freeze verifier revisions, policies, and acceptance boundary;
5. freeze metrics, missingness handling, statistical tests, and analysis code;
6. preserve exact-revision failures, blocked interventions, and mixed cells;
7. requalify any selected path affected by historical #207/#208/#212 authority ordering against accepted #288;
8. rebase/requalify #323 before using the Workbench for authoritative trials;
9. keep #341 research-only until its own frozen governed experiment is complete;
10. preserve any #338 protected ownership/requalification dependency required by the selected path;
11. independently qualify the selected evidence path to the degree required by the scientific claim;
12. retain any WebVM/provider/release qualification required by that selected path;
13. preserve negative, rejected, `UNKNOWN`, `BLOCKED`, missing, and failed cells in the evidence package.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a sibling job, rerun, or later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- A research workflow may PASS because it successfully captured a scenario-level FAIL; distinguish experiment execution from hypothesis outcome.
- Do not inherit qualification from a predecessor branch or predecessor main SHA after `main` materially moves.
- A successful sub-check inside a required multi-stage qualification run does not override that run's terminal FAIL.
- Do not infer model quality from transport conformance, physical iOS reliability from browser preflight, or production readiness from fixture CI.
- A merge does not turn missing review evidence into PASS.
- Retain exact commit/tree, workload hash, model/config identity, and raw observations for every paper-facing result.

## Current empirical boundary

The repository has strong development evidence for mechanisms and exact-revision integration, plus useful positive and negative real-model/stress evidence. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That remains the major scientific milestone.
