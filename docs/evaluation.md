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

Current `main` is **`e996b58566847e88153e6e5196625d52b93e081a`**, created by merged #185.

The accepted lineage includes #179's bounded browser build-output handling, #183's provider-session lifecycle behavior, and #185's release-stabilization integration. #185 accepts a narrowly bounded protected `runtime_journal.py` writer-admission retry with the corresponding ownership-baseline advance and the #186 iOS/WebKit pre-boot walkthrough fallback.

Latest observed applicable exact-current-main runs are PASS: Factory ownership, clean install, measured-evaluation binding, M4 prerequisites, Controller/provider, Command Station, iOS WebKit preflight and Pages/deployment.

Retain the important same-SHA exception: Controller/provider run **`35263782697`** is **FAIL** in Python 3.13, while later run **`35264069649`** on the same current-main SHA is PASS. The exact cause of the earlier failure is **UNKNOWN** from the retained evidence reviewed here. Do not collapse this history into an unqualified “all green” claim or infer a code-level fix from an unchanged-SHA rerun.

Current-main Command Station run `35264069706` is PASS. Older `main@2e1341c9...` Command Station run `35219212073` remains historical FAIL evidence. Pages run `35263783090`, attempt 1, is PASS.

This is mechanism/integration/browser evidence. It is **not** a live R0–R5 result, paid/live provider/model quality evidence, physical heavy-WebVM reliability evidence, long-run production-reliability evidence, independent scientific validation or a paper-facing effect size.

The older protected M4 `/proc/<pid>/status` observation-race FAIL also remains in the evidence record. Acceptance of #185's separate protected runtime-journal change does not establish root cause or repair of that older protected failure.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

#179 changed the bounded build path and truncation classification but did not prove truncation caused the historical failures. #183 addresses provider-session lifecycle behavior but does not itself constitute live semantic acceptance evidence.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and proceeds through normal verifier/receipt handling. If a study depends on the real-provider path, do not substitute green provider-contract or Pages/browser CI for fresh exact-revision provider evidence.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. Retained diagnostics isolate a process-local CPython positive-duration timed-wait failure under WebVM. Existing recovery, diagnostics, provider-session handling, and current iOS fallback are bounded mitigations/controls; none proves the historical guest-corruption root cause or an acceptable long-run recurrence rate.

The #186 fallback is now accepted on main through #185. Current-main iOS WebKit preflight is PASS for the specific contract that the unsupported/unqualified iOS WebKit profile reaches the lightweight walkthrough before heavyweight guest/disk boot.

That result must **not** be reported as physical heavy-WebVM reliability. Published physical-device validation remains open, and the exact internal WebKit process-kill mechanism remains **UNKNOWN**.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. preserve the same-SHA Controller/provider FAIL alongside the later PASS;
4. define a repeated-run reliability campaign in advance;
5. preserve every first-attempt `FAIL`/`UNKNOWN` rather than rerunning it away;
6. report operational failure/missingness separately from model correctness;
7. do not describe a safe fallback, provider-session repair, narrow mitigation or added telemetry as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

The #185 protected runtime-journal bytes and ownership-baseline advance are now accepted on current main. Their accepted behavior is limited to bounded retry during mutation-free SQLite writer transaction admission on genuine BUSY/LOCKED contention; mutation/COMMIT are not replayed after transaction admission.

This is separate from the historical protected `/proc` observation-race lineage. PR #139 remains the isolated repair lane where applicable. If a selected evidence path depends on #139 or downstream #134, preserve the complete sequence:

1. evaluate the protected change under the applicable trust-boundary review policy;
2. make any ownership-baseline advancement deliberately;
3. run fresh qualification after a protected pin change;
4. refresh/requalify dependent work against the new accepted revision.

Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

## Qualification v1 and inference-economics candidates

PR #152 proposes a broader fail-closed qualification methodology. Any result from an older base is historical to that exact head and does not constitute current-main qualification.

Interpretation boundaries:

- virtual-day stress is fixture stress, not elapsed wall-clock soak;
- planned 24h/72h/30d workflows are not evidence until those runs actually complete;
- a live-provider canary proves at most one bounded adapter execution/evidence path, not provider/model quality;
- the framework does not replace capable-runner M4, ownership or Pages acceptance gates;
- retained current-revision failures must remain represented as `FAIL`, not hidden by aggregate sibling or rerun success.

PR #177 remains the development-only IE-001 prototype qualification candidate. Its prior focused PASS/maintainer evidence is historical to its candidate head and must be reconciled/refreshed against the current IE-001 contract and applicable current-main qualification before final IE-001 qualification is claimed. It is not production runtime evidence, a real-provider/GPU benchmark or a paper-facing result.

Draft #178 is documentation-only follow-on implementation backlog for IE-002 through IE-007 and makes no speedup/cost/routing/GPU/paper claim. Draft #175 remains specification-only OpenViking/context-provider planning.

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
6. preserve and explicitly scope the retained same-SHA Controller/provider FAIL for the selected evidence path;
7. independently qualify the selected evidence path to the degree required by the scientific claim;
8. retain any WebVM/provider/release qualification required by that selected path;
9. preserve negative, rejected, `UNKNOWN`, missing and failed cells in the evidence package.

Green fixture/package checks do not substitute for this freeze/qualification sequence.

## Recommended qualification ladder

1. **Clean install** — installed package/import/asset/CLI checks on the exact revision.
2. **Exact-main regression state** — preserve and explain retained exact-revision `FAIL` evidence before promoting broader qualification.
3. **Selected backend/evidence path** — prove execution identity, anti-replay, workload mapping, evidence completeness and verifier boundary.
4. **Environment-specific runtime qualification** — WebVM/provider/cluster path only if the study uses it.
5. **Frozen R0–R5 study** — one fixed model under the preregistered schedule.
6. **Model degradation** — progressively weaker workers, unchanged acceptance policy.
7. **Heterogeneous routing** — mixed local/remote/cheap/strong workers under the same evidence boundary.
8. **Fault campaign** — worker termination, stale telemetry, network interruption, invalid receipts, verifier failure and recovery cases.
9. **24-hour soak** — only after shorter qualification is clean.
10. **72-hour soak** — only after the 24-hour run is clean.
11. **30-day soak** — long-duration operational evidence after shorter gates are stable.

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
