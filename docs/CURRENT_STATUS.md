# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against current `main` at `2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-head workflow output, retained machine-readable artifacts, submitted review/attestation records and explicit open issues are more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform includes requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution and bounded self-maintenance research.

The repository contains substantial implementation and qualification evidence for its mechanisms. It does **not** yet claim that the central reliability hypothesis is proven on live heterogeneous models, that WebVM reliability has an acceptable long-run failure rate, that the historical guest-corruption family has been root-caused, that current main is fully green, that release/recovery qualification is complete, or that production soak targets have been met.

## Current main and recent merges

Current `main` is **`2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`**, tree **`6751f3c21a53bff725fe0e4c89b0d56004c2f44d`**.

Recent material merges are:

- **#159 / `ddf339a9...`** — fresh-overlay recovery for a poisoned WebVM Mission Control guest. The durable poison fence remains fail closed; recovery replaces the writable guest overlay rather than clearing poison in place.
- **#168 / `faae2e28...`** — solo-maintainer governance. Repository merge control is automated qualification plus exact-head maintainer attestation. This is not a claim of independent human assurance.
- **#153 / `2b7cb626...`** — bounded WebVM terminal-proof marker plus post-run control-unlock synchronization. It consolidates the relevant #150/#140 acceptance-harness repairs without changing provider authority, Factory/M4 implementation or shared evidence schemas.

## Current-main qualification — FAIL / incomplete

The exact current-main push is **not fully green**.

Observed retained outcomes include:

- measured-evaluation binding — **PASS** (`35172926292`);
- Command Station — **PASS** (`35172926302`);
- Pages/WebVM — **PASS** (`35172926305`, attempt 1);
- Controller/provider contracts — **FAIL** (`35172926291`).

The Controller/provider workflow failed in the Python 3.12 full-suite lane. The authoritative error is:

`test_factory_m4_safety.FixtureSupervisorTests.test_timeout_kills_process_group_not_only_parent`

The test observed `/proc/<pid>/status` existing, then the process disappeared before `status.read_text()`, producing `FileNotFoundError`. The Python 3.11 lane completed successfully; Python 3.13 was cancelled after the matrix failure. The full current-main workflow therefore remains **FAIL**. Do not convert it to `PASS` from the successful sibling lanes and do not rerun the failure away as though it never occurred.

This is the same protected M4 qualification-test observation race isolated by PR #139. The failure is evidence about the qualification surface; it is not evidence that the #153 browser-acceptance changes introduced a provider/controller defect.

## WebVM production/recovery evidence

### Retained production failure before #159

Fresh post-#156 iPhone/WebKit public-demo evidence reached **`Provider connected`** but the Linux guest exposed **`RESIDUAL_WORKER_POISONED`** while Mission Control remained at **`GUEST STARTING`** with no supported recovery path.

That observed end-to-end mission is **FAIL** at the guest-recovery/product boundary. It does not prove a provider-model failure: no valid live candidate completed the normal RESIDUAL verifier/receipt path. Successful paid/live Puter candidate execution remains **UNKNOWN**.

The poison fence is intentional fail-closed behavior. The lower-level cause of that production poison remains **UNKNOWN**.

### #159 recovery integration

#159 preserves the poisoned old guest and rotates to a fresh browser-session WebVM writable overlay. Its exact candidate head `5c33f31d...` had the observed automated/browser qualification set green, including Browser VM Demo CI and Pages proof. Its browser acceptance deliberately reproduced poison, required `GUEST FAILED · RESTART REQUIRED`, rotated the guest, proved poison/PID/control/busy/active-lock state did not carry over, and completed a real local repository audit. Cloud/provider behavior in that proof was test-double coverage, not live model quality.

The first production Pages run after #159 retained a **FAIL** in narrow-browser proof: deployment and desktop proof passed, but the proof parser read a real `:0` command-exit marker as `:0503`. That first failure remains authoritative evidence and was not rewritten.

### #153 acceptance-proof repair

#153 repairs that browser-proof boundary with a terminated exit marker and the bounded post-run control-unlock synchronization. Its final exact head `80c0e5f8...` had all observed applicable workflows green, including the maintainer-approval gate, and carried an exact-head maintainer attestation before merge.

Current-main Pages run `35172926305` is **PASS**, demonstrating the merged browser acceptance path can publish successfully on this revision. That is browser/deployment evidence only. It does **not** establish a fresh successful paid/live Puter mission on real iPhone/WebKit. That end-to-end provider result remains **UNKNOWN** until retained live-account evidence exists.

## WebVM reliability boundary

Issues **#120** and **#126** remain open. Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around call 273, while tested direct libc waits continue beyond that boundary. Merged #145 routes long-lived browser polling below the known Python timed-wait surface.

The production poisoned-guest event is additional reliability evidence. The relationship between that poison event, the timed-wait failure and the older `_sha512`/impossible-constructor/allocator corruption family remains **UNKNOWN**. Avoidance of one known trigger is not root-cause proof and does not establish an acceptable recurrence rate.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues **#63** and **#48** are closed. `implementation-status.yaml` correctly records implementation presence; it is not a production-qualification manifest.

Current-main ordinary CI is red on the protected M4 safety-test observation race. PR **#139** remains the isolated repair lane for the `/proc/<pid>/status` TOCTOU. Because that repair changes a protected qualification byte, the required sequence is deliberately separate from ordinary documentation work:

1. evaluate the protected change under the applicable trust-boundary review policy;
2. if accepted, deliberately advance the ownership baseline rather than changing it merely to obtain green;
3. run fresh qualification after any protected pin change;
4. only then refresh/requalify downstream #134.

This documentation branch changes no Factory/M4 implementation, protected test byte, ownership baseline, qualification anchor or shared evidence schema.

## Governance boundary

Merged PR **#168** establishes the repository's solo-maintainer approval model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

The maintainer approval gate accepts a qualifying write/maintain/admin human maintainer's exact-head attestation and fails closed for stale heads, malformed/revoked attestations, bots and insufficient roles.

This model should be described as **maintainer-reviewed with automated qualification**. It explicitly does **not** establish independent human assurance. #146's proposed generic repository-wide independent-human merge gate was closed unmerged/superseded by #168.

Independent or third-party evidence may still be required by a specific security, release or research claim. Governance does not relax those claim-specific evidence requirements.

## Other active work

- **#152** — broader Qualification v1 framework. Any pre-current-main aggregate qualification is historical; it must be refreshed/requalified before use as current release evidence. Virtual/simulated time is not elapsed soak.
- **#139** — protected M4 observation-race repair; trust-boundary sequence above remains open.
- **#134** — provider-adapter hardening remains downstream of the protected #139 sequence.
- **#89** — historical onboarding/Inspector lane retains its own historical browser evidence; #153 merging does not automatically rewrite that branch's result.
- **#160–#167** — inference-engineering proposals/specifications are planning artifacts unless and until their implementation and exact-head qualification land. They do not change `implementation-status.yaml` by themselves.

## Research and release non-claims

The project does **not** yet claim that:

- live heterogeneous models prove a material reliability gain under the frozen acceptance boundary;
- paid/live Puter execution succeeds end to end on exact current main;
- current main is fully green while Controller/provider run `35172926291` is retained `FAIL`;
- WebVM long-run reliability is acceptable or the historical corruption family is root-caused;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- blank-environment release qualification or actual host-loss recovery is complete;
- the solo-maintainer governance model supplies independent human assurance;
- autonomous recursive self-improvement or autonomous merge authority has been demonstrated.

## Next gates

1. Preserve current-main Controller/provider run `35172926291` as **FAIL** and resolve the protected M4 `/proc` observation race through the #139 protected-byte/ownership-baseline sequence.
2. After any accepted #139 integration, obtain fresh exact-revision qualification before using it to unblock #134.
3. Run a fresh retained real-account iPhone/WebKit mission on the merged #159 + #153 surface. Successful paid/live provider execution stays `UNKNOWN` until that evidence exists.
4. Keep #120/#126 open and run a predefined retained reliability campaign rather than inferring long-run reliability from individual green Pages runs.
5. Refresh/requalify #152 against current main; do not inherit stale-head aggregate release claims.
6. Execute true blank-environment/recovery qualification without promoting rehearsal/simulation to release `PASS`.
7. Freeze confirmatory live-evaluation workload, models/configuration, verifier policy, metrics and analysis before outcome access; then run R0–R5, degradation and heterogeneous-routing studies.
8. Progress through elapsed 24h → 72h → 30-day soak only after the shorter gates are clean.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head workflow output and retained machine-readable artifacts;
3. open qualification/security/reliability issues that narrow claims;
4. submitted maintainer/review records and the applicable governance policy;
5. this current-status document;
6. `implementation-status.yaml` and generated implementation summary for implementation traceability;
7. historical specs/snapshots for design intent, not current implementation claims.

RESIDUAL's strongest research claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are checked, and only evidence-backed results are allowed to become accepted state.
