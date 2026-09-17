# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against current `main` at `160c01a1b1933ee10c82dcf30b1674a17f7560ff`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-head workflow output, retained machine-readable artifacts, submitted maintainer/review records and explicit open issues are more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform includes requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution and bounded self-maintenance research.

The repository contains substantial implementation and qualification evidence for its mechanisms. Exact current main has a green observed automated/browser/deployment workflow set. The repository does **not** yet claim that the central reliability hypothesis is proven on live heterogeneous models, that paid/live Puter inference succeeds end to end on this exact revision, that WebVM reliability has an acceptable long-run failure rate, that the historical guest-corruption family has been root-caused, that release/recovery qualification is complete, or that production soak targets have been met.

## Current main and recent merge

Current `main` is **`160c01a1b1933ee10c82dcf30b1674a17f7560ff`**, tree **`ce59882b03f593bbc000104c32cd90f40509bef0`**.

The material change since `77f16362...` is merged **PR #169**, “Demo diagnostic telemetry and triage bundles.” Its final head was **`fb767dc9682533a6092eb36de783e15a3bd47c13`**.

#169 adds:

- local-first session/run/event correlation for the public WebVM demo;
- a bounded 5,000-event / 1 MiB session-local diagnostic buffer;
- sanitized downloadable diagnostic bundles;
- browser/runtime/UI/guest-projected metadata sufficient for triage without retaining prompts or provider response content;
- bounded service-worker disk-chunk retry/exhaustion diagnostics without request URLs or payloads.

Its trust boundary is explicit: diagnostics are observational only. Retained guest trace plus `verify-trace` remain authoritative execution evidence. Telemetry does not schedule, retry, terminate, authorize, alter provider routing, modify evidence, or determine mission success.

The exact final #169 head completed the required exact-head qualification and received visible maintainer attestation `RESIDUAL-MAINTAINER-APPROVAL: fb767dc9682533a6092eb36de783e15a3bd47c13` before merge. Under the solo-maintainer policy that supports the wording **maintainer-reviewed with automated qualification**. It is not independent human assurance.

No Factory/M4 protected implementation or qualification byte, ownership pin, shared evidence schema, provider authorization rule, candidate acceptance rule or research threshold is changed by #169.

## Current-main qualification — observed automated/browser set PASS

All seven observed `push` workflows on exact current main completed **PASS**:

| Workflow | Exact-current-main outcome |
| --- | --- |
| Factory ownership gate | **PASS** — run `35182396486` |
| Clean install qualification | **PASS** — run `35182396556` |
| Measured evaluation acceptance binding | **PASS** — run `35182396462` |
| M4 qualification runner prerequisites | **PASS** — run `35182396481` |
| Controller and provider contracts | **PASS** — run `35182396520` |
| Command Station checks | **PASS** — run `35182396476` |
| Deploy GitHub Pages | **PASS** — run `35182396521` |

Pages/WebVM run **`35182396521`** completed **PASS** on attempt 1. Its retained path includes provider-session/publication contract checks, static-site and pinned-WebVM build, immutable guest-image identity, generated desktop+narrow real-browser proof, deployment, published WebVM revision and real-guest execution, published narrow-Chromium acceptance, and retained live-acceptance proof.

That is exact-revision automated/browser/deployment evidence. It does **not** establish successful paid/live Puter inference, model quality, long-run WebVM reliability, blank-machine release qualification or elapsed soak.

### Historical protected M4 failure remains evidence

The earlier `main@2b7cb626...` retained Controller/provider run `35172926291` as **FAIL** in the Python 3.12 full-suite lane. The failing protected safety test was `test_factory_m4_safety.FixtureSupervisorTests.test_timeout_kills_process_group_not_only_parent`: `/proc/<pid>/status` disappeared between an existence check and `read_text()`, raising `FileNotFoundError`.

The current-main Controller/provider workflow is green, but that does not erase the earlier exact-revision failure or prove the protected observation race fixed. PR **#139** remains the isolated protected-test repair lane. Its required protected-byte sequence remains: review the protected change under the applicable trust-boundary policy, deliberately advance the ownership baseline if accepted, run fresh qualification after any pin change, and only then refresh/requalify downstream #134.

## Live provider evidence

### Fresh retained real-account failure

Fresh real iPhone/WebKit + Puter evidence from mission **`m-b98fe1b9beb440cdb1b8dfe855ad5778`** reached `openai/gpt-5.4-nano` twice. Both separately counted calls ended **`provider_protocol_invalid`**. No candidate crossed the protocol boundary: `candidate_rejections=0` and `verification_elapsed_ms=0`.

The retained run also shows that the browser build mission was bounded to **1536 provider-output tokens** while requiring the complete generated file bundle inside the worker envelope.

Claim discipline for this result:

- live-provider path result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**, because no candidate crossed the protocol boundary;
- semantic verifier result: **UNKNOWN / not run**;
- cause of the invalid responses: **UNKNOWN**; the 1536-token ceiling is a plausible constraint exposed by the evidence, not proof of sole causality.

The earlier real-account `provider_protocol_invalid` evidence on `2b7cb626...` remains historical FAIL/BLOCKED evidence and is not rewritten by later transport changes.

### PR #176 — bounded build-output candidate

PR **#176**, “Demo: give generated builds enough bounded provider output,” proposes:

- build-only public output ceiling/default from 1536 to 8192;
- non-build/source-grounded live mode remains capped at 1536;
- browser provider relay accepts the same bounded 8192 build request;
- normalized `finish_reason=length` becomes `provider_protocol_invalid / response_truncated`;
- worker-envelope validation, candidate validation, verifier authority, call budgets, evidence binding, M4 and artifact path/size controls remain unchanged.

Its current head **`faba8cea0e47fd6068e7fa00469e9ee8018b1064`** received an exact-head maintainer attestation and has substantial exact-head green CI evidence, but it was built from `77f16362...` and is now **diverged from current `main@160c01a1...`**. Those results are therefore historical to that candidate head. Refresh/current-main integration plus fresh exact-head qualification is required before integration.

Even after any accepted #176 merge, the live-provider claim remains gated on a **new retained real-account iPhone/WebKit mission**. Do not infer success from provider-contract or Pages/browser CI alone.

## WebVM reliability boundary

Issues **#120** and **#126** remain open. Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around the same narrow call boundary, while tested direct libc waits continue beyond it. Merged #145 routes long-lived browser polling below the known Python timed-wait surface.

The production poisoned-guest event is additional reliability evidence. The relationship between that poison event, the timed-wait failure and the older `_sha512`/impossible-constructor/allocator corruption family remains **UNKNOWN**. Avoidance of one known trigger is not root-cause proof and does not establish an acceptable recurrence rate.

Merged #159 preserves the poison fence and recovers by rotating to a fresh browser-session WebVM writable overlay. Merged #153 repairs the later narrow-browser terminal-proof parser/control-unlock acceptance issue. Merged #169 improves local diagnostic capture. These are bounded recovery/acceptance/triage improvements; they do not prove long-run guest reliability.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues **#63** and **#48** are closed. `implementation-status.yaml` correctly records implementation presence; it is not a production-qualification manifest.

PR **#139** remains the isolated protected `/proc/<pid>/status` observation-race repair. This documentation branch changes no Factory/M4 implementation, protected test byte, ownership baseline, qualification anchor or shared evidence schema.

PR **#134** remains downstream of that protected sequence where its qualification depends on the repaired/pinned surface. A green sibling/provider/browser lane does not substitute for completing the protected-byte process.

## Governance boundary

Merged PR **#168** establishes the repository's solo-maintainer approval model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

The maintainer approval gate accepts a qualifying write/maintain/admin human maintainer's exact-head attestation and fails closed for stale heads, malformed/revoked attestations, bots and insufficient roles.

This model should be described as **maintainer-reviewed with automated qualification**. It explicitly does **not** establish independent human assurance. Claim-specific independent or third-party evidence may still be required by security, release or research claims.

## Other active work

- **#177** — draft IE-001 inference-economics prototype qualification candidate. The focused prototype suite reports **203 passed**; its branch reports Q1–Q10/equivalent automated evidence and maintainer governance PASS, but **Q11 genuinely independent current-head technical review remains pending**, so final IE-001 qualification is not claimed. Its branch was created from pre-#169 main; current-main qualification is not inherited.
- **#178** — draft documentation-only implementation backlog for IE-002 through IE-007. It explicitly records follow-on work rather than promoting uploaded prototype code into production and makes no runtime speedup, token/cost, routing, GPU or paper-facing claim.
- **#175** — draft, specification-only OpenViking/context-provider integration proposal. It introduces no runtime dependency and no accepted implementation claim.
- **#152** — broader Qualification v1 framework. Any pre-current-main aggregate qualification is historical; it must be refreshed/requalified before use as current release evidence. Virtual/simulated time is not elapsed soak.
- **#139** — protected M4 observation-race repair; the trust-boundary sequence above remains open.
- **#134** — provider-adapter hardening remains downstream of the protected #139 sequence where that dependency applies.

## Research and release non-claims

The project does **not** yet claim that:

- live heterogeneous models prove a material reliability gain under the frozen acceptance boundary;
- paid/live Puter execution succeeds end to end on exact current main;
- current-main green Pages/browser evidence is equivalent to live-provider success or long-run reliability;
- the 1536-token build ceiling is proven to be the sole cause of the retained protocol failures;
- #176 is current-main-qualified or proves live-provider success;
- a green current Controller/provider run proves the historical protected M4 race is fixed;
- WebVM long-run reliability is acceptable or the historical corruption family is root-caused;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- blank-environment release qualification or actual host-loss recovery is complete;
- the solo-maintainer governance model supplies independent human assurance;
- #177 has final IE-001 qualification;
- draft #175/#178 planning is accepted runtime capability;
- autonomous recursive self-improvement or autonomous merge authority has been demonstrated.

## Next gates

1. Refresh #176 onto current accepted main, rerun exact-head qualification and maintainer governance, and preserve any first failure rather than rerunning it away.
2. If #176 is accepted and merged, require first-attempt post-merge Pages/browser qualification and then a fresh real-account iPhone/WebKit mission before any positive live-provider claim.
3. Resolve the protected M4 `/proc` observation race through #139's protected-byte/ownership-baseline sequence and freshly requalify any dependent #134 work.
4. Keep #120/#126 open and run a predefined retained reliability campaign rather than inferring long-run reliability from individual green Pages runs.
5. Refresh/requalify #152 against current main; do not inherit stale-head aggregate release claims.
6. Execute true blank-environment/recovery qualification without promoting rehearsal/simulation to release `PASS`.
7. Keep #177 as a candidate until its explicit Q11 independent-review gate is satisfied on the applicable head; do not promote prototype results into production claims.
8. Freeze confirmatory live-evaluation workload, models/configuration, verifier policy, metrics and analysis before outcome access; then run R0–R5, degradation and heterogeneous-routing studies.
9. Progress through elapsed 24h → 72h → 30-day soak only after shorter gates are clean.

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
