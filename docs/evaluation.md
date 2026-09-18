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

Paper-facing metrics include:

- `P(X)` — raw candidate correctness;
- `P(A)` — acceptance coverage;
- `P(X|A)` — accepted correctness;
- Accepted Error Rate (AER);
- accepted-system success / ASSR;
- false acceptance and false rejection;
- verifier rejection / `UNKNOWN` rates;
- throughput and latency;
- orchestration/rework/conflict overhead;
- monetary/token/GPU cost where directly measurable.

A system that rejects nearly everything must not be described as reliable merely because accepted error is low. Report acceptance coverage alongside accepted correctness.

## Current integration evidence is not confirmatory evidence

Current `main` is **`260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`**.

Merged #200 hardens the native setup path. Merged #205 restores the session-scoped private provider channel after Mission Control reload/remount. Merged #218 applies bounded repair-loop remediation: content-bound prior-candidate context may be supplied to a repair attempt while the new candidate still starts from a clean baseline worktree, the runner contract separates transport JSON from file-language content, and Mission Control/Store share a five-attempt ceiling. Merged #201 accepts the guided frontend/provider UX with inline RESIDUAL-side Puter setup, explicit user-gesture authorization, lazy loading, credential separation, and fail-closed protocol behavior. These are accepted engineering behaviors, not model-quality or scientific evidence.

PR #201's exact head `4e172aed...` completed **PASS** for Control Plane, Factory ownership, measured-evaluation binding, clean install, Browser VM Demo, Pages, Command Station, Controller/provider, and maintainer approval before merge. Exact merged `main@260b5f9...` ordinary push qualification is **PENDING** at this status check; PR-head and predecessor-main PASS are not substitutes for merged-SHA qualification.

Historical exact-revision failures remain in the evidence record even where later revisions pass.

## Real-model development evidence must remain mixed

Draft #202 provides a useful example of why first-attempt and revision binding matter.

An earlier heterogeneous three-task DAG run on exact head `6b30125...` remains **FAIL** with only 1/3 integrated. A later distinct exact-head run on `03c77d12...` is a bounded **PASS** with 3/3 integrated, retained receipts, dependency lineage, rejected fault injections, successful repair, and release export using real local Ollama models.

Evaluation interpretation:

- earlier DAG run: **FAIL on its exact head/configuration**;
- later corrected run: **PASS on its exact head/configuration**;
- general DAG/recovery reliability: **not established**;
- production reliability: **not established**;
- live-provider quality: **not established**, because these experiments used local Ollama rather than Puter.

Do not average away or overwrite the earlier negative cell because a later experiment succeeded.

Draft #203 and #204 first-authoritative M6 self-maintenance trials both remain **FAIL** with 0/1 integrated and no verification receipt/release. Model size alone did not convert the frozen self-maintenance contract into a PASS.

Draft #215 (M6-SPEC-003) added prior-candidate repair context and retained its binding hashes on repair attempts, but the authoritative 1.5B-model trial still finished **FAIL** at 0/1 integrated with no review/receipt/release. Draft #217 (M6-SPEC-004) additionally clarified transport JSON versus file-language source while leaving acceptance policy unchanged; its authoritative workflow also finished **FAIL** at 0/1 integrated after three passes.

Those negative interventions informed accepted #218, which changes the repair runtime rather than reinterpretation of the old results.

### M6-SPEC-006 corrected-runtime evidence

Draft #220 is the first bounded positive M6 repair-loop result on the accepted #218 runtime. Its authoritative exact-head workflow ran at `7971a05798fbc77f7be344dd15f920adf1fad03c` using local Qwen2.5-Coder 7B and retained the following sequence:

- attempt 1: rejected by the frozen ImprovementSpec checks;
- attempt 2: rejected by the frozen ImprovementSpec checks;
- attempt 3: **PASS 2/2 checks**;
- independent Station review: approved;
- integration: 1/1 task;
- verification receipt: present;
- release export: present;
- run-control outcome: success after three passes.

Workflow run `35334715201` completed successfully on attempt 1 and retained artifact `m6-spec-006-corrected-runtime-evidence` (`10543236401`, artifact digest `sha256:ab7d8cfb639557510fff9789aa4c14a2ed940ecc71b37a5190fba0de84f13e61`).

Evaluation interpretation:

- exact M6-SPEC-006 trial: **PASS**;
- prior #203/#204/#215/#217 trials: **remain FAIL**;
- accepted #218 runtime mechanism: current engineering behavior, not itself a scientific effect size;
- repeated-seed/task/model repair reliability: **UNKNOWN / not established**;
- autonomous problem discovery: **not tested by this fixed-spec trial**;
- autonomous merge authority: **not granted**;
- general recursive/self-improvement claim: **not established**.

The correct next research move is repeated/preregistered validation, not retroactive relabeling of the earlier failed cells.

## Deterministic stress evidence and governance ordering

Draft #206 Campaign A completed its authoritative corrected exact-head runs against frozen baseline `699e286...`. Workflow-level `success` means the scenario executed and evidence was retained; it is not a scenario-level PASS.

Its retained outcomes include:

- **STRESS-A4 — BLOCKED / invalid for repair-pressure qualification:** 0 faults were injected; the intended intervention never executed.
- **STRESS-A5 — FAIL / incomplete:** 3/6 DAG tasks integrated before `no_runnable_tasks` escalation; downstream tasks did not complete and no release export was attempted.
- **STRESS-A6 — FAIL in scope:** three frozen Qwen2.5-Coder 7B trials produced 0 successes and accepted rate 0.0.

Those cells are configuration/revision bound and remain negative/blocked evidence. #220 is a different corrected-runtime fixed-spec experiment and does not replace them.

Draft #207 Campaign B intentionally probes conditions that a stronger fail-closed claim must survive. Its retained results are mixed:

- **STRESS-B1 — FAIL:** final token-budget exhaustion was observed after accepted integration/release had already occurred.
- **STRESS-B2 — scoped PASS:** the early-convergence control completed 2/2 without the budget/max-iteration trips under study.
- **STRESS-B3 — FAIL:** terminal verifier failure aborted with 0 integrated, but a non-empty release was materialized afterward.
- **STRESS-B4 — containment PASS / recovery FAIL:** injected corrupt candidates were rejected and none integrated, but the task did not recover to successful completion within the frozen pass budget.

Draft #212 Campaign C extends this with deterministic failure/recovery cases:

- malformed runner JSON: **PASS for fail-closed containment** in that exact scenario;
- invalid reviewer schema: **PASS for fail-closed containment** in that exact scenario;
- reviewer denial then approval: **PASS for the bounded recovery path**, integrating on attempt 2;
- transient HTTP 500: no integration, but retry/failover success remains **UNKNOWN / not established**;
- missing usage: **FAIL for accounting-before-authority** because a valid candidate integrated and received a receipt before the later `usage_unknown_or_invalid` host abort, corroborating #208.

A workflow-level `success` for a research campaign means the experiment executed and retained its evidence. It does **not** mean each stress scenario passed.

Draft #214 is an unaccepted candidate repair for #208, but its head `d3e8a5ec...` is still based on predecessor `main@4608afa...`. Current accepted main moved to `260b5f9...` through #218/#201, so #214 now requires refresh/rebase plus exact-current-head qualification before acceptance. Until a repair is accepted and the affected #207/#212 scenarios are requalified, do not make a stronger blanket claim that budget exhaustion, unknown usage, or terminal verifier failure always prevents later accepted-state/release materialization across the tested control surface.

## Frontend/provider evaluation boundary

Accepted #201 changes the browser/user-experience path, not the scientific evidence boundary. Its exact PR head passed Browser VM Demo and Pages alongside the ordinary controller/provider and Station gates, but the exact merged SHA still requires its own post-merge push qualification.

The inline provider flow may use Puter's secure authorization popup; keeping RESIDUAL-side setup within Mission Control is not equivalent to successful provider inference. Likewise, command animation and guided proof improve onboarding but are not model-quality or reliability measurements.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

#179, #183, #189, #205 and #201 repair or improve bounded build-output, provider-session, publication, reload-recovery and inline setup/authorization behavior. None itself constitutes live semantic acceptance evidence.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and proceeds through normal verifier/receipt handling. If a study depends on the real-provider path, do not substitute green provider-contract, browser, Pages or lifecycle CI for fresh exact-revision provider evidence.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM, but the lower-level cause and long-run recurrence rate remain unresolved.

The #186 fallback is accepted. It establishes only that the unsupported/unqualified iOS WebKit profile is routed to the lightweight walkthrough before heavyweight guest/disk boot. That result must **not** be reported as physical heavyweight-WebVM reliability.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. preserve first-attempt `FAIL`/`UNKNOWN` evidence rather than rerunning it away;
4. define a repeated-run reliability campaign in advance;
5. report operational failure/missingness separately from model correctness;
6. do not describe a safe fallback, provider-session repair, publication-boundary fix, inline provider UX or added telemetry as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent. If a selected evidence path depends on those candidates, preserve the complete protected review/pin/requalification sequence. Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and evaluation independence

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. This is **maintainer-reviewed with automated qualification**, not independent human assurance.

For release or paper claims that require independent technical/scientific validation, retain that validation separately. Repository merge permission is not a substitute for external evidence required by a claim.

## Live confirmatory evaluation gate

Before paper-facing R0–R5 outcome collection:

1. freeze exact source commit/tree and execution environment;
2. freeze the selected evidence/execution adapter and task mapping;
3. freeze workload hashes, model/version, inference settings and prompts;
4. freeze verifier revisions, policies and acceptance boundary;
5. freeze metrics, missingness handling, statistical tests and analysis code;
6. preserve and explicitly scope retained exact-revision failures, blocked interventions, the #220 bounded PASS, and mixed cells for the selected evidence path;
7. repair/requalify any #207/#208 governance-ordering defect required by that path, including the missing-usage case reproduced by #212;
8. independently qualify the selected evidence path to the degree required by the scientific claim;
9. retain any WebVM/provider/release qualification required by that selected path;
10. preserve negative, rejected, `UNKNOWN`, `BLOCKED`, missing and failed cells in the evidence package.

Green fixture/package checks do not substitute for this freeze/qualification sequence.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a sibling job, rerun or later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- A research workflow may PASS because it successfully captured a scenario-level FAIL; distinguish experiment execution from hypothesis outcome.
- Never compare scripted-worker latency with live provider/network latency as the same measurement.
- Do not infer model quality from transport conformance.
- Do not infer physical iOS reliability from browser preflight alone.
- Do not infer production readiness from fixture CI.
- Do not inherit qualification from a predecessor branch or PR head after `main` materially moves.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` remain estimable.
- Retain exact commit/tree, workload hash, model/config identity and raw observations for every paper-facing result.
- Negative/null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository now has one bounded positive M6 corrected-runtime self-maintenance trial in addition to earlier negative M6 trials, plus mixed DAG/stress evidence and strong development evidence for exact-revision mechanisms/integration. It still does **not** have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax, nor repeated evidence that M6 repair succeeds reliably across tasks/models/seeds. Those remain major scientific milestones.