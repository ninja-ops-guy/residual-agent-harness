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

Failures, abstentions, and missing usage remain in denominators. Missing provider usage remains unknown rather than being reported as zero-cost evidence.

## Frozen reliability evaluation

The research apparatus includes immutable workload definitions, repeated configuration runs, ablations, statistics/comparison reports, fault injection, evidence/report reconstruction, and Factory measurement hooks.

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

Current `main` is **`b3f00af29c7507f4c0e218884e491c2fc792d984`**.

Since the previously documented `dcf1e507...` state:

- #188 merged AQ-GOV-001, a bounded adversarial authority-escalation lab;
- #194 merged completed-draft visibility/reopen behavior in Command Station;
- #133 merged WebVM runtime discriminator tooling and also removed the previously accepted #132 self-hosting/research-bundle surface.

Six of seven ordinary first-attempt `push` workflows on exact current main have completed **PASS**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, and Command Station. Pages/deployment run `35288585007` remains **IN PROGRESS / PENDING**. Do not inherit predecessor-main or candidate-head PASS for the remaining deployment gate.

On the exact #133 final candidate head, ordinary Factory ownership, measured-evaluation binding, Browser VM Demo, Control Plane, clean install, Controller/provider, Command Station, Pages, and maintainer approval completed **PASS**. Several WebVM discriminator workflows intentionally completed **FAIL** after reproducing the runtime defect being studied. Those retained FAILs are experimental observations, not qualification PASSes and not flaky failures to erase through rerun.

This is mechanism/integration/diagnostic evidence. It is **not** a live R0–R5 result, paid/live provider/model-quality evidence, physical-device reliability evidence, long-run production-reliability evidence, independent scientific validation, or a paper-facing effect size.

## WebVM diagnostic evaluation boundary

Retained #133 evidence materially narrows one WebVM runtime symptom:

- positive-duration `time.sleep()` reproduces `_PyTime_t` overflow around a narrow process-local call boundary;
- empty `select.select([], [], [], timeout)` reproduces the same failure family;
- zero-duration sleep and tested monotonic clock reads pass beyond the same boundary;
- native i386 controls pass;
- direct libc `nanosleep` / `clock_nanosleep` controls continue beyond the same boundary;
- paired fresh-process tests show replacement resets or avoids the process-local boundary;
- Mission Control, its persistent worker, a second interpreter, and background scheduling are not necessary preconditions.

The supported interpretation is a **WebVM-specific CPython positive-duration timeout/wait conversion-path failure** affecting at least sleep and empty-select in the tested guest/runtime combination.

The following remain **UNKNOWN / unestablished**:

- exact CPython/i386 ABI, time64, emulation, syscall/handle/resource, or conversion cause;
- causal significance of time64 `ENOSYS` observations;
- relationship to historical `_sha512`, impossible-constructor, allocator, or poisoned-guest evidence;
- long-run recurrence rate;
- production fix.

Therefore #133 diagnostic PASS/FAIL evidence must not be converted into a blanket WebVM reliability PASS.

## Historical #132 evidence and current evaluation surface

Merged #132 previously retained a bounded protected self-hosting/research-bundle experiment with exact-head evidence. Its scope was deliberately narrow and did not claim repeated live autonomous self-improvement or autonomous merge authority.

Merged #133 removed #132's implementation, workflow, tests, example, and dedicated research docs from current main. Earlier #133 review explicitly identified those deletions as an integration blocker for a diagnostic-only PR.

Evaluation interpretation:

- #132 results remain historical evidence for their exact source revision;
- the #132 tooling is **not available as current accepted evaluation apparatus** on `main@b3f00af...`;
- the reason for removal is **UNKNOWN** from retained evidence;
- no current evaluation plan should assume that tooling exists unless it is deliberately restored/reintroduced and requalified.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded build path, #183 changed provider-session lifecycle handling, and #189 repaired a provider-helper publication boundary. The historical failure remains evidence and successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses provider protocol validation and normal verifier/receipt handling.

PR #190 remains open/unaccepted and predates current main. Any earlier exact-head candidate evidence is historical after the material main move. Refresh/requalification and any required post-merge production retest remain separate gates.

If a study depends on the real-provider path, do not substitute green provider-contract, browser, or Pages CI for fresh exact-revision provider evidence.

## WebVM-dependent evaluation gate

Issues #120/#126 remain open. #133 provides substantially stronger discriminators but does not close long-run reliability or root-cause questions.

For a confirmatory protocol that depends on WebVM:

1. freeze the exact source and deployed revision;
2. retain browser/runtime qualification artifacts for that exact revision;
3. preserve first-attempt `FAIL`/`UNKNOWN` evidence rather than rerunning it away;
4. define a repeated-run reliability campaign in advance;
5. report operational failure/missingness separately from model correctness;
6. do not describe a diagnostic discriminator, safe fallback, provider-session repair, publication-boundary fix, or added telemetry as proof that the broader corruption family is fixed.

A protocol may exclude WebVM, but exclusion must be explicit before outcome access.

## AQ-GOV-001 evaluation boundary

Merged #188 is accepted adversarial test/research apparatus. It deliberately assumes unanimous worker approval and tests whether existing host-side software controls still deny a fixed set of authority escalations while allowing a harmless positive control.

A green AQ-GOV-001 run supports only the tested software-path invariant. It does not establish resistance to a kernel, container, hypervisor, broker, credential-service, or other implementation escape. Those require separate qualification.

## Protected Factory/M4 evidence path

M4 remains evidence- and environment-bound rather than universally qualified.

Accepted #185/#187 protected changes remain scoped to their reviewed bytes. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent. If a selected evidence path depends on it, preserve the complete protected review/pin/requalification sequence. Do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

## Qualification and research candidates

PR #152 proposes a broader fail-closed qualification methodology. Any result from an older base is historical to that exact head and does not constitute current-main qualification.

PR #177 remains a development-only IE-001 prototype qualification candidate. Its prior evidence is historical to its candidate head and must be reconciled/refreshed against current main/current IE-001 policy before final qualification is claimed.

PR #193 remains an unaccepted setup-script candidate based on an older main state. PR #191 was closed unmerged and is not accepted evaluation/governance infrastructure.

## Governance and evaluation independence

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. This is **maintainer-reviewed with automated qualification**, not independent human assurance.

For release or paper claims that require independent technical/scientific validation, retain that validation separately. Repository merge permission is not a substitute for external evidence required by a claim.

## Live confirmatory evaluation gate

Before paper-facing R0–R5 outcome collection:

1. freeze exact source commit/tree and execution environment;
2. freeze the selected evidence/execution adapter and task mapping;
3. freeze workload hashes, model/version, inference settings, and prompts;
4. freeze verifier revisions, policies, and acceptance boundary;
5. freeze metrics, missingness handling, statistical tests, and analysis code;
6. preserve and explicitly scope retained exact-revision failures for the selected evidence path;
7. independently qualify the selected evidence path to the degree required by the scientific claim;
8. retain any WebVM/provider/release qualification required by that selected path;
9. preserve negative, rejected, `UNKNOWN`, missing, and failed cells in the evidence package;
10. do not rely on removed #132 tooling unless it is deliberately restored/reintroduced and qualified on the selected source revision.

Green fixture/package checks do not substitute for this freeze/qualification sequence.

## Interpretation rules

- `PASS` is scoped to the named revision/environment/gate.
- `FAIL` remains evidence even if a sibling job, rerun, or later revision passes.
- `UNKNOWN` means causality/evidence/qualification is unresolved.
- `BLOCKED` means the required gate could not validly execute; it is not `PASS`.
- An intentional diagnostic FAIL that reproduces the target defect remains a FAIL observation; it is not silently relabeled PASS.
- Never compare scripted-worker latency with live provider/network latency as the same measurement.
- Do not infer model quality from transport conformance.
- Do not infer physical iOS reliability from browser preflight alone.
- Do not infer production readiness from fixture CI.
- Do not inherit qualification from a predecessor branch after `main` materially moves.
- Keep worker correctness independent from controller acceptance so `P(X)` and `P(X|A)` remain estimable.
- Retain exact commit/tree, workload hash, model/config identity, and raw observations for every paper-facing result.
- Negative/null results belong in the evidence package; do not tune the frozen protocol after observing them.

## Current empirical boundary

The repository has strong development evidence for mechanisms, adversarial-control testing, and a materially narrowed WebVM runtime symptom, plus retained negative evidence that must remain visible. It does **not** yet have confirmatory live evidence that the reliability architecture materially increases `P(X|A)` over `P(X)` at useful coverage and acceptable orchestration tax. That remains the major scientific milestone.
