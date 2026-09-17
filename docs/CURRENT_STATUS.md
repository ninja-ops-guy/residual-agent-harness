# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against current `main` at `2e1341c99fd7b72452e3b8c5278b1f557871b783`._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-head workflow output, retained machine-readable artifacts, submitted maintainer/review records and explicit open issues are more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform includes requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability, operator surfaces, browser/WebVM execution and bounded self-maintenance research.

Current main includes the accepted browser build-output mitigation from #179 and the accepted mobile provider-session lifecycle repair from #183. The exact #183 candidate head completed its observed PR qualification and maintainer gate, but the exact merged revision is **not all-green**: six of seven observed `push` workflows are **PASS**, while Command Station checks are retained **FAIL** in the Python 3.11 full-suite lane. The precise Python 3.11 failure cause remains **UNKNOWN** from the retained workflow metadata currently available. Pages/browser deployment on the same merged revision is **PASS**.

Fresh physical-device evidence still shows a separate iPhone/WebKit runtime failure on the heavyweight WebVM path. Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established**. The project does not claim acceptable long-run WebVM reliability, root cause of the historical corruption family, completed release/recovery qualification, elapsed soak completion, or confirmatory proof of the central reliability hypothesis.

## Current main and recent accepted change

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`**, tree **`1b044f03d786911f69b91c0a63cc855b5de73226`**.

It was created by merging **PR #183**, “Mobile provider: survive iOS tab suspension and reload,” on top of predecessor `250494f2c1aa57aa37545761b675bc76a6eacdba`.

#183 addresses a provider-session lifecycle defect observed during mobile use. It:

- extends browser-side provider liveness grace to five minutes;
- refreshes liveness on bounded valid provider traffic rather than heartbeat state alone;
- preserves the private BroadcastChannel capability in provider-tab `sessionStorage` after removing it from the visible URL;
- allows a reloaded provider tab to recover that capability and reuse an already signed-in Puter session when `isSignedIn()` remains true;
- preserves bfcache pages and re-advertises provider state on foreground/page restoration.

Its authority boundary is unchanged: no raw provider output retention, hidden/uncounted model call, model substitution, worker-envelope weakening, verifier/receipt authority change, poison/fresh-overlay change, Factory/M4 change, shared evidence-schema change, provider max-call increase or per-mission grant extension is accepted by this merge. #183 does **not** claim to fix the separate iPhone/WebVM crash.

The exact final #183 head **`0b520064cb9deff32dc7d1c261dcaf99f3dc2848`** completed all observed exact-head PR workflows **PASS**, including Factory ownership, clean install, measured binding, Control Plane, Controller/provider, Browser VM Demo CI, Command Station, Pages and the maintainer approval gate. Visible exact-head maintainer attestation was submitted before merge. Under the solo-maintainer policy this supports the wording **maintainer-reviewed with automated qualification**. It is not independent human assurance.

No protected Factory/M4 implementation or qualification byte, ownership pin, qualification anchor or shared evidence schema is modified by this documentation refresh.

## Exact-current-main qualification — mixed PASS/FAIL

Seven `push` workflows were observed on exact current main. Six completed **PASS** and one completed **FAIL**.

| Workflow / gate | Exact-current-main outcome |
| --- | --- |
| Measured evaluation acceptance binding | **PASS** |
| Clean install qualification | **PASS** |
| Factory ownership gate | **PASS** |
| Controller and provider contracts | **PASS** |
| M4 qualification runner prerequisites / applicable main gate | **PASS** |
| Deploy GitHub Pages | **PASS** — run `35219212133`, attempt 1 |
| Command Station checks | **FAIL** — run `35219212073`, attempt 1 |

The Command Station workflow failure is localized in the retained job metadata to the **Python 3.11** job, specifically `python -m unittest discover -s tests -v`. The browser job, Docker job, Python 3.12 job and Python 3.13 job passed. The exact failing unittest/test identity is not established by the workflow metadata currently retained here, so the failure cause is **UNKNOWN** rather than guessed.

This failure remains authoritative evidence for exact current main. It is not erased by the all-green #183 candidate head, successful sibling jobs, or a later rerun unless code/evidence changes justify a new exact-revision claim.

Pages run **`35219212133`** completed **PASS** on attempt 1 on exact current main, including generated build/browser proof and deployment. That evidence establishes only its named automated/browser/deployment scope. It does **not** establish paid/live Puter success, physical iPhone/WebKit reliability, model quality, long-run WebVM reliability, blank-machine release qualification or elapsed soak.

### Historical protected M4 failure remains evidence

The earlier `main@2b7cb626...` retained Controller/provider run `35172926291` as **FAIL** in the Python 3.12 full-suite lane. The protected safety test `test_factory_m4_safety.FixtureSupervisorTests.test_timeout_kills_process_group_not_only_parent` observed `/proc/<pid>/status` disappearing between existence checking and `read_text()`, producing `FileNotFoundError`.

Later green runs do not erase that exact-revision failure or prove the protected observation race fixed. PR **#139** remains the isolated protected-test repair lane. Its required sequence remains: review the protected change under the applicable trust-boundary policy, deliberately advance the ownership baseline only if accepted, run fresh qualification after any pin change, and only then refresh/requalify dependent #134 work.

## Live-provider evidence

### Historical retained protocol failure

Retained real iPhone/WebKit + Puter mission **`m-b98fe1b9beb440cdb1b8dfe855ad5778`** reached `openai/gpt-5.4-nano` twice. Both separately counted calls ended **`provider_protocol_invalid`**. No candidate crossed the protocol boundary: `candidate_rejections=0` and `verification_elapsed_ms=0`.

Claim discipline for that result remains:

- historical live-provider path result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verifier result: **UNKNOWN / not run**;
- cause of the invalid responses: **UNKNOWN**.

The historical run used a 1536-token browser-build provider-output bound. Merged #179 raised only the browser build ceiling/default to 8192, retained 1536 for non-build/source-grounded live mode, and classified normalized truncation/incomplete completion fail-closed as `provider_protocol_invalid / response_truncated`. The historical evidence did not prove truncation was the sole/root cause, so #179 remains a bounded mitigation and better classification rather than causal closure.

A **fresh retained real-account Puter mission on exact deployed current main** is still required before successful paid/live provider execution can become `PASS`. It must cross the provider protocol boundary and proceed through normal verifier/receipt handling. Green provider-contract or Pages/browser CI is not a substitute for that evidence.

### #183 accepted; post-merge real-device provider-session proof still open

Merged #183 addresses the browser provider-session follow-up/reload lifecycle, but no post-merge physical-device provider-session retest is promoted here to `PASS`. The implementation and automated qualification are accepted; the real-device behavioral claim remains open until retained post-merge evidence exercises the affected follow-up/reload path.

Provider-session recovery and iPhone WebVM runtime reliability are separate gates. A provider-session success does not prove the WebVM crash fixed, and a safe mobile runtime path does not prove model/candidate correctness.

## Physical iPhone/WebKit reliability boundary

Issue **#120** retains fresh physical-device evidence from predecessor live `main@250494f2...`:

- PC/desktop: public demo works through the provider/build path;
- iPhone/WebKit: heavyweight WebVM/demo path crashes;
- the same session exposed the separate provider reconnect/re-auth symptom addressed by #183.

No retained typed iPhone browser exception/crash artifact is available from that report, so the exact internal WebKit process-kill mechanism remains **UNKNOWN**. It must not be reclassified as provider-model failure, and successful narrow-Chromium Pages proof does not erase it.

PR **#182**, exact head `dc1e4233f1fc801c2265ad793b5d7d000c2a1473`, is the bounded mobile presentation/capability candidate. It inserts an iOS/iPadOS preflight before heavyweight WebVM boot and defaults detected iOS WebKit to the lightweight `/walkthrough/` engineer experience, with `?full_vm=1` retained as an explicit diagnostic override.

At that exact head:

- dedicated **iOS WebKit preflight**: **PASS**;
- Browser VM Demo CI: **PASS**;
- Controller/provider: **PASS**;
- Command Station: **PASS**;
- clean install, Factory ownership, measured binding, Control Plane and Pages: **PASS**;
- maintainer approval gate: **FAIL/BLOCKED**.

The branch was created from predecessor main and now predates merged #183. Therefore it must be refreshed onto current accepted main, freshly requalified, and receive a qualifying exact-head maintainer attestation before any merge. After any accepted merge, require the exact merged revision's first production Pages result and a physical iPhone/WebKit retest. No physical-iPhone `PASS` is claimed today.

## WebVM reliability boundary

Issues **#120** and **#126** remain open. Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around the same narrow call boundary, while tested direct libc waits continue beyond it. Merged #145 routes long-lived browser polling below the known Python timed-wait surface.

The retained reliability campaign also contains a later long-lived guest failure after multiple passes, while a separate fresh-process hammer passed its tested cases. Those observations narrow the problem but do not establish a root cause. The relationship among the physical iPhone/WebKit crash, production poisoned-guest event, timed-wait failure and older interpreter/allocator corruption family remains **UNKNOWN**.

Merged #159 provides whole-guest fresh-overlay recovery while preserving the poison fence. Merged #153 repairs narrow-browser terminal-proof/control-unlock acceptance. Merged #169 adds privacy-safe local diagnostics. Merged #179 changes the bounded browser build-output path. Merged #183 changes provider-session lifecycle handling. These are bounded improvements; none by itself proves acceptable long-run guest reliability.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues **#63** and **#48** are closed. `implementation-status.yaml` correctly records implementation presence; it is not a production-qualification manifest.

PR **#139** remains the isolated protected `/proc/<pid>/status` observation-race repair. This documentation branch changes no Factory/M4 implementation, protected test byte, ownership baseline, qualification anchor or shared evidence schema.

PR **#134** remains downstream of that protected sequence where its qualification depends on the repaired/pinned surface. Green sibling/provider/browser lanes do not substitute for completing the protected-byte process.

## Governance boundary

Merged PR **#168** establishes the repository's solo-maintainer approval model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

The maintainer approval gate fails closed for stale heads, malformed/revoked attestations, bots and insufficient roles.

This model should be described as **maintainer-reviewed with automated qualification**. It explicitly does **not** establish independent human assurance. Claim-specific independent or third-party evidence may still be required by security, release or research claims.

## Other active work

- **#182** — open iOS/WebKit pre-boot safe-mode candidate. All observed technical workflows are PASS on its current exact head, but maintainer approval is **BLOCKED** and the branch predates the #183 main move; refresh/requalification and physical post-merge testing are still required.
- **#180** — open narrow standalone generated-build consistency candidate. Its prior technical qualification is historical to its predecessor base after #183 moved main; it remains unaccepted and is not a browser-demo blocker.
- **#177** — draft IE-001 inference-economics prototype qualification candidate. The focused prototype suite reports **203 passed**; Q11 genuinely independent current-head technical review remains pending, so final IE-001 qualification is not claimed. Its branch predates current main.
- **#178** — draft documentation-only implementation backlog for IE-002 through IE-007; no runtime speedup, token/cost, routing, GPU or paper-facing claim.
- **#175** — draft specification-only OpenViking/context-provider integration proposal; no runtime dependency or accepted implementation claim.
- **#152** — broader Qualification v1 framework. Any prior aggregate qualification is historical to its head and must be refreshed/requalified before use as current release evidence. Virtual/simulated time is not elapsed soak.
- **#139** — protected M4 observation-race repair; protected-byte/ownership-baseline/fresh-qualification sequence remains open.
- **#134** — downstream provider-adapter hardening remains dependent on the protected sequence where applicable.

## Research and release non-claims

The project does **not** yet claim that:

- exact current main has an all-green observed workflow set;
- the Python 3.11 Command Station failure cause is known;
- live heterogeneous models prove a material reliability gain under the frozen acceptance boundary;
- paid/live Puter execution succeeds end to end on exact current main;
- #183 has post-merge physical-device provider-session acceptance evidence;
- current-main green Pages/browser evidence is equivalent to physical iPhone/WebKit reliability, live-provider success or long-run reliability;
- the physical iPhone/WebKit crash is root-caused or fixed;
- #182 is accepted/effective on a physical device;
- the historical 1536-token build ceiling is proven to be the sole/root cause of retained protocol failures;
- a later green Controller/provider run proves the historical protected M4 race is fixed;
- WebVM long-run reliability is acceptable or the historical corruption family is root-caused;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- blank-environment release qualification or actual host-loss recovery is complete;
- the solo-maintainer governance model supplies independent human assurance;
- #177 has final IE-001 qualification;
- draft/open planning and candidates are accepted runtime capability;
- autonomous recursive self-improvement or autonomous merge authority has been demonstrated.

## Next gates

1. Preserve and triage current-main Command Station run `35219212073` as **FAIL**. Identify the Python 3.11 failing test from retained evidence before claiming causality or closure; do not rerun unchanged code merely to obtain green.
2. Refresh #182 onto exact accepted current main, rerun the full exact-head qualification set, obtain exact-head maintainer attestation, and only after any accepted merge perform first-attempt production Pages plus physical iPhone/WebKit retest.
3. Retest the #183 provider-session follow-up/reload path on a physical device and retain the first result separately from the WebVM runtime outcome.
4. Retain a fresh real-account Puter build on the exact deployed accepted revision; do not claim live-provider `PASS` unless a valid candidate crosses the protocol boundary and proceeds truthfully through normal verifier/receipt handling.
5. Resolve the protected M4 `/proc` observation race through #139's protected-byte/ownership-baseline sequence and freshly requalify any dependent #134 work.
6. Keep #120/#126 open and continue retained reliability work rather than inferring long-run reliability from isolated green Pages runs or a safe mobile fallback.
7. Refresh/requalify #152 against current main; do not inherit stale-head aggregate release claims.
8. Execute true blank-environment/recovery qualification without promoting rehearsal/simulation to release `PASS`.
9. Keep #177 as a candidate until its explicit Q11 independent-review gate is satisfied on the applicable head.
10. Freeze confirmatory live-evaluation workload, models/configuration, verifier policy, metrics and analysis before outcome access; then run R0–R5, degradation and heterogeneous-routing studies.
11. Progress through elapsed 24h → 72h → 30-day soak only after shorter gates are clean.

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
