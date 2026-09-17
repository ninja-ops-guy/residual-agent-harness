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

Current `main` is **`dcf1e5071deb624c637aa72df575089435d72ac9`**, created by merged #189 on top of merged #187.

#187 accepted the protected M4 safety-test `/proc/<pid>/status` observation repair and corresponding ownership pin. Its exact-head automated qualification and maintainer approval were PASS before merge. That is scoped protected-test evidence, not a universal every-host M4 claim.

#189 accepted a Pages isolation-boundary repair that keeps `/provider/` outside COOP/COEP response rewriting while preserving `/demo/` and heavyweight WebVM isolation. Its exact-head Factory ownership, clean install, measured binding, Control Plane, Controller/provider, Command Station, Browser VM Demo, Pages and maintainer approval workflows were PASS before merge.

The first exact-current-main post-#189 push/deployment workflows were **still queued at the latest observation**. Therefore post-merge current-main qualification/deployment is **PENDING**, not inferred PASS from pre-merge CI.

Historical Controller/provider run `35263782697` on `main@e996b585...` remains retained **FAIL** in Python 3.13. #187 diagnoses/repairs the protected-test observation race, but the historical failure stays in the evidence record.

This is mechanism/integration/browser evidence. It is **not** a live R0–R5 result, paid/live provider/model-quality evidence, physical heavyweight-WebVM reliability evidence, long-run production-reliability evidence, independent scientific validation or a paper-facing effect size.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

#179 changed the bounded build path and truncation classification but did not prove truncation caused the historical failures. #183 addresses provider-session lifecycle behavior but does not itself constitute live semantic acceptance evidence. #189 repairs the provider helper's static COI/CORP publication boundary but still requires exact-merged-revision deployment and retained production verification.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and proceeds through normal verifier/receipt handling. If a study depends on the real-provider path, do not substitute green provider-contract, browser, or pre-merge Pages CI for fresh exact-revision provider evidence.

PR #190 proposes additional provider-channel recovery after Mission Control reload. Its recorded base predates #189 and it must be refreshed/requalified before any evaluation path relies on it.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM. Existing recovery, diagnostics, provider-session handling, iOS fallback, and #189 provider-helper publication repair are bounded mitigations/controls; none proves the historical guest-corruption root cause or an acceptable long-run recurrence rate.

The #186 fallback is accepted. It establishes only that the unsupported/unqualified iOS WebKit profile is routed to the lightweight walkthrough before heavyweight guest/disk boot. That result must **not** be reported as physical heavyweight-WebVM reliability.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. preserve first-attempt `FAIL`/`UNKNOWN` evidence rather than rerunning it away;
4. define a repeated-run reliability campaign in advance;
5. report operational failure/missingness separately from model correctness;
6. do not describe a safe fallback, provider-session repair, publication-boundary fix or added telemetry as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

The #185 protected runtime-journal bytes and ownership-baseline advance remain accepted. #187 additionally accepts the protected test observation repair and its ownership pin. Their accepted behavior is limited to the reviewed changes.

The separate #139→ownership-baseline→#134 sequence remains independent. If a selected evidence path depends on those candidates, preserve the complete protected review/pin/requalification sequence. Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

## Qualification and research candidates

PR #152 proposes a broader fail-closed qualification methodology. Any result from an older base is historical to that exact head and does not constitute current-main qualification.

PR #177 remains a development-only IE-001 prototype qualification candidate. Its prior evidence is historical to its candidate head and must be reconciled/refreshed against current main/current IE-001 policy before final qualification is claimed.

PR #188 is an additive AQ-GOV-001 consensus-authority escalation lab candidate. Until merged and qualified, it is not accepted research evidence; even if green, its scope does not prove kernel/container/hypervisor/broker escape resistance.

PR #191 is an unaccepted automated PR-review workflow candidate and is not part of the repository's evaluation/governance evidence until merged and qualified.

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
6. preserve and explicitly scope retained exact-revision failures for the selected evidence path;
7. independently qualify the selected evidence path to the degree required by the scientific claim;
8. retain any WebVM/provider/release qualification required by that selected path;
9. preserve negative, rejected, `UNKNOWN`, missing and failed cells in the evidence package.

Green fixture/package checks do not substitute for this freeze/qualification sequence.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a sibling job, rerun or later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- Never compare scripted-worker latency with live provider/network latency as the same measurement.
- Do not infer model quality from transport conformance.
- Do not infer physical iOS reliability from browser preflight alone.
- Do not infer production readiness from fixture CI.
- Do not inherit qualification from a predecessor branch after `main` materially moves.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` remain estimable.
- Retain exact commit/tree, workload hash, model/config identity and raw observations for every paper-facing result.
- Negative/null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository has strong development evidence for mechanisms and exact-revision integration, plus retained failure history that must remain visible. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That remains the major scientific milestone.
