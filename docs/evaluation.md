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

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged #330. No newer production-main commit landed in this check.

Recent accepted engineering/security changes include #307 CI fan-out repair, #260 provider-bootstrap hardening, #288 pre-dispatch Station budget authority, #320 repository-side CSP/anti-clickjacking configuration, #328 core execution/egress/XML security hardening, and #330 workflow checkout credential-persistence hardening. These are engineering, governance, or security changes, not model-quality or scientific evidence.

Accepted #276 requires each `main` SHA to receive its own non-cancelling production Pages attempt. For exact current main, run **`35437556200`**, attempt 1, completed **FAIL**. Generated artifact/browser proof, deployment, served revision identity, and desktop real-guest acceptance passed; the required narrow/mobile Chromium acceptance failed after reaching the live guest and multiple Workbench stages. The retained live-proof artifact is `10582812524`, SHA-256 `868ca31506d278a335ff95d3607adbd13c14edaec8b161c1b45ac013e7f7c8b8`. The lower-level cause remains **UNKNOWN**.

Production Pages run `35431634267`, attempt 1, remains a scoped **PASS for exact revision `0a675017...` only**. The earlier Pages **FAIL** on `e7b72ad...` also remains exact-revision evidence. Neither predecessor result overrides the independent current-main FAIL.

Open #336 has a generated branch Pages **PASS** at exact head `92aca285...`, but it is not accepted-current-main evidence. It remains on HOLD behind #337 because review of #336 exposed a PR Agent fail-open publication/concurrency defect. #337's technical lanes are green in their scoped checks, but PR Agent advisory and protected maintainer approval remain **FAIL**, so the governance repair is itself unaccepted. If #337 lands, #336 must reconcile and regenerate exact-head evidence; if #336 later lands, the new main SHA still requires its own first authoritative production Pages attempt.

Successful paid/live Puter execution, every-host M4 qualification, production Vercel security-header validation, blank-environment install, physical heavyweight-WebVM reliability, and a scientific effect size remain separate claims. The current Pages failure recorded `cloud_inference` as `NOT_RUN`, so it is not a live-provider/model-quality failure result.

## Real-model development evidence must remain mixed

Draft #202 provides a useful example of why first-attempt and revision binding matter. An earlier heterogeneous three-task DAG run remains **FAIL**, while a later distinct exact-head run is a bounded **PASS** with 3/3 integrated, retained receipts, dependency lineage, rejected fault injections, successful repair, and release export using real local Ollama models. The later PASS does not erase the earlier FAIL or establish general DAG/recovery reliability.

The M6 self-host sequence is similarly mixed: #203/#204/#215/#217 retain authoritative **FAIL** cells, while #220/M6-SPEC-006 retains one bounded corrected-path **PASS**. That PASS does not establish general autonomous self-maintenance.

## M6.2 discovery evaluation boundary

The autonomous-discovery series must be evaluated as a matrix of scoped outcomes rather than one aggregate success claim.

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

Merged **#288** closes product issue #208. The accepted repair adds host-owned pre-dispatch budget/deadline admission for Station runner/reviewer calls, conservative handling of invalid/unknown usage, authority rechecks, and release export bound to a successful exact-head/spec run-control result.

Interpretation discipline:

- product defect #208: **repaired/accepted on main**;
- historical #207/#212 scenario outcomes: unchanged retained evidence;
- stronger present-tense claim that the repaired path prevents every affected authority-ordering failure: **UNKNOWN pending fresh repaired-path requalification**.

Do not retroactively relabel frozen FAIL cells as PASS because a repair later merged.

## Research Workbench evaluation boundary

Draft #323's first authoritative Workbench trial remains **BLOCKED**. #288 is now accepted, satisfying one prerequisite, but #323 still requires rebase/requalification onto a main containing that repair before an authoritative M6-WB-001 run.

Definition availability for staged Workbench experiments is not execution evidence.

## Cooperative mesh evaluation

#319 / M6-MESH-001 Trial 0 is a bounded positive pilot. Both sequential and two-call concurrent conditions passed their six obligation checks; retained means were about 2.1899 s sequential and 1.8300 s concurrent across three repeats on one Ollama host.

That cell supports only the observation made under its frozen conditions. Warm-up/order sensitivity and the small sample mean that statistically durable concurrency benefit and general mesh/swarm efficiency remain **UNKNOWN / not established**.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and proceeds through normal verifier/receipt handling.

Do not substitute green provider-contract, browser, Pages-build, or lifecycle CI for fresh exact-revision provider evidence.

## Security qualification is separate from scientific evaluation

Merged #320, #328, and #330 are accepted configuration/source/workflow changes, but their existence does not turn security or scientific claims into blanket PASS.

- #320 production Vercel response-header enforcement/Aikido revalidation: **UNKNOWN / pending**.
- #328 core source/runtime security split: **accepted** for its reviewed scope.
- #330 checkout credential-persistence hardening: **accepted** for its reviewed workflow scope.
- stale overlapping #324: must not be merged wholesale.
- vendor/scanner confidence: not repository acceptance evidence and not scientific evidence.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Bounded mitigations, diagnostics, and individual green runs do not establish an acceptable long-run recurrence rate or a complete root cause.

The #186 fallback is accepted. It establishes only that the unsupported/unqualified iOS WebKit profile is routed to the lightweight walkthrough before heavyweight guest/disk boot. That result must **not** be reported as physical heavyweight-WebVM reliability.

The exact-current-main Pages result adds one more bounded negative cell: desktop real-guest execution passed in run `35437556200`, while the required narrow/mobile Chromium proof failed. Preserve that asymmetry rather than flattening it into either blanket browser failure or mobile reliability proof. The #336 branch-only generated Pages PASS is a separate changed-head engineering observation, not a rewrite of the production FAIL.

For a confirmatory protocol that depends on WebVM: freeze the exact source/deployed revision, retain exact-revision browser/runtime evidence, preserve first-attempt `FAIL`/`UNKNOWN`, preregister repeated reliability measurement, report operational missingness separately from model correctness, and never describe a safe fallback or transport repair as proof that the broader reliability family is fixed.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent.

Qualification-v1 remains a separate testing-branch evidence path. Reverse-merge **#333** moved open PR #152 to exact head **`11c0ac67f60f61a7243bcc79ce803d588a89aa94`**. Exact-head Qualification-v1 run **`35443955204` attempt 1 = FAIL**. Its retained final manifest lists `deterministic-regression`, `qualification-selftests`, and `toxic-provider-matrix` as required non-PASS gates. The deterministic regression gate retained seven enterprise sandbox test failures because the hosted runner reported `kernel-level sandbox isolation unavailable`, alongside 1,817 passed tests, 29 skips, and 387 passed subtests. The selftest and toxic-provider gates each failed because the full provider-mission qualifier returned FAIL; the lower-level provider-mission cause remains **UNKNOWN** from retained evidence.

On the same exact testing head, Factory ownership, M4 prerequisites, Browser VM Demo, Controller/provider contracts, Command Station, clean install, Factory runtime/OS evidence, Control Plane, measured-evaluation binding, and generated PR Pages proof are **PASS**. Those partial PASSes do not override the aggregate required-gate FAIL. Protected maintainer approval and PR Agent advisory are also **FAIL**. The predecessor `24816ebc...` positive technical evidence remains historical and exact-head bound; it is not inherited after the reverse merge.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and evaluation independence

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. This is **maintainer-reviewed with automated qualification**, not independent human assurance.

The #336/#337 finding is itself evidence for keeping advisory publication fail closed: a fresh bot failure/status message is not a substantive review. #337 remains unaccepted until its required gates pass; #336 remains held behind it.

Issue #305's historical Actions saturation remains evidence. #307 is accepted as the structural duplicate-fan-out repair. The current queued-run snapshot is **0**; queue state never permits required first-attempt failures to be cancelled or reinterpreted.

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
9. independently qualify the selected evidence path to the degree required by the scientific claim;
10. retain any WebVM/provider/release qualification required by that selected path;
11. preserve negative, rejected, `UNKNOWN`, `BLOCKED`, missing, and failed cells in the evidence package.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a sibling job, rerun, or later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- A research workflow may PASS because it successfully captured a scenario-level FAIL; distinguish experiment execution from hypothesis outcome.
- Do not inherit qualification from a predecessor branch or predecessor main SHA after `main` materially moves.
- A successful sub-check inside a required multi-stage qualification run does not override that run's terminal FAIL.
- Do not infer model quality from transport conformance, physical iOS reliability from browser preflight, or production readiness from fixture CI.
- Retain exact commit/tree, workload hash, model/config identity, and raw observations for every paper-facing result.

## Current empirical boundary

The repository has strong development evidence for mechanisms and exact-revision integration, plus useful positive and negative real-model/stress evidence. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That remains the major scientific milestone.
