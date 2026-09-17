# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against `main@dcf1e5071deb624c637aa72df575089435d72ac9`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` advanced from `e996b585...` through two accepted merges:

- **#187** — protected M4 safety-test repair for the `/proc/<pid>/status` exit-observation race, plus the corresponding Factory ownership-baseline pin advance. This repairs test observation of an expected disappearing child process; it does not establish a runtime termination defect or universal M4 qualification.
- **#189** — GitHub Pages isolation fix that exempts the optional `/provider/` helper from COOP/COEP response rewriting while preserving `/demo/` and heavyweight WebVM isolation. This addresses the observed Puter SDK CORP failure at the static publication boundary.

Current `main` is **`dcf1e5071deb624c637aa72df575089435d72ac9`**, the merge commit for #189. Its parent `8592ba3b331c4d9cc16e038d0e9d7cdbfa6fbf24` is the #187 merge.

Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established**. Physical heavyweight-WebVM reliability on iPhone/Safari remains **UNKNOWN / unqualified**. Blank-environment install, host-loss/recovery evidence, selected elapsed soak, and confirmatory R0–R5 research remain open.

## Accepted protected Factory change: #187

PR #187 final head was `6a5ee753abe6137214f3ee17c8bcc4a85c4f3461`; it merged as `8592ba3b331c4d9cc16e038d0e9d7cdbfa6fbf24`.

The change is intentionally narrow:

- reads `/proc/<pid>/status` once instead of checking existence and then reopening it;
- treats only `FileNotFoundError` / `ProcessLookupError` as the successful disappeared-process outcome;
- preserves the bounded polling window and failure when a live non-zombie child remains;
- changes no runtime code, capability probe, verifier rule, evidence schema, or acceptance semantic;
- deliberately advances the protected ownership pin for the changed test blob.

Exact-head automated qualification on the #187 candidate was PASS for Factory ownership, measured binding, M4 runner prerequisites, clean install, Control Plane, Controller/provider, and Command Station. The exact-head maintainer approval gate also completed PASS before merge.

Those results support the scoped protected-test change. Hosted/prerequisite PASS is not, by itself, universal capable-runner M4 qualification, and the historical failure remains retained evidence.

## Provider helper publication boundary: #189

PR #189 final head was `a307460228d1f1562805856085d471915f93e3f4`; it merged as current main `dcf1e5071deb624c637aa72df575089435d72ac9`.

The diagnosed defect was that the root `coi-serviceworker.js` controlled `/provider/` and injected COOP/COEP headers into the provider-helper navigation response. That placed the helper under `Cross-Origin-Embedder-Policy`, causing `https://js.puter.com/v2/` to fail with CORP / `net::ERR_FAILED` and the UI to report that the SDK could not load.

The accepted fix bypasses COOP/COEP response rewriting only for same-origin requests under the service-worker-relative `/provider/` path. `/demo/` and the heavyweight WebVM isolation boundary remain unchanged. No M4/runtime/provider protocol/call-budget/verifier/evidence-schema authority is changed.

Exact-head #189 PR workflows were PASS for Factory ownership, clean install, measured evaluation binding, Control Plane, Controller/provider, Command Station, Browser VM Demo, Deploy GitHub Pages, and the maintainer approval gate.

## Exact-current-main qualification

The first post-merge push workflows for exact `main@dcf1e507...` were **still queued at the latest observation**. Therefore:

- accepted code state: **PASS / on main**;
- pre-merge exact-head #189 technical qualification: **PASS within the named workflows**;
- first post-merge #189 current-main workflow/deployment set: **PENDING / not yet qualified PASS**;
- production provider-helper SDK/sign-in behavior after #189: **UNKNOWN until retained post-deploy verification exists**.

Do not convert the pre-merge Pages PASS into a post-merge production PASS. The first production Pages attempt on the merged SHA remains an explicit gate.

Historical retained evidence remains visible. Controller/provider run `35263782697` on `main@e996b585...` is retained **FAIL** in Python 3.13. #187 identifies and repairs that protected-test observation race; the historical FAIL is not erased by the later repair or by same-SHA rerun success.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of those historical invalid responses: **UNKNOWN**.

Merged #179 is a bounded build-output/truncation mitigation. Merged #183 is a provider-session lifecycle repair. Merged #189 repairs the provider helper's COI/CORP publication boundary. None alone establishes successful live inference.

A fresh retained real-account mission on the exact deployed accepted revision is required before paid/live provider success can become PASS. It must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling.

## iPhone/WebKit boundary

The accepted #186 fallback detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot and routes that profile to `/walkthrough/?platform=ios-webkit`, retaining `?full_vm=1` only as an explicit diagnostic override.

This is a fallback contract, not proof that heavyweight WebVM is reliable on physical iPhone Safari. Published physical-device validation remains open, and the lower-level WebKit process-kill cause remains **UNKNOWN**.

## Open provider-session candidate: #190

PR **#190** proposes recovery of the Mission Control provider BroadcastChannel token from same-tab `sessionStorage` after Mission Control reload/discard so it can reattach to the surviving provider setup tab.

The candidate changes browser session ownership/recovery only and explicitly does not claim live Puter success, provider quality, physical-iPhone reliability, blank-environment qualification, elapsed soak, or production reliability.

Its recorded base is `main@8592ba3b...`, before #189. It therefore requires refresh/reconciliation against current main and fresh exact-head qualification before integration. It is **unaccepted**.

## WebVM reliability boundary

Issues #120 and #126 remain open. Historical diagnostics narrow a WebVM-specific, process-local CPython positive-duration timed-wait failure, but the relationship among that family, the physical iPhone crash, poisoned-guest events, and older interpreter/allocator corruption evidence remains **UNKNOWN**.

Merged #159, #153, #169, #179, #183, #185/#186, and #189 are bounded improvements. None alone establishes an acceptable long-run guest failure rate or a complete root cause for the broader corruption family.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

The #185 protected runtime-journal/ownership-baseline change remains accepted. #187 additionally accepts the protected test-only `/proc` observation-race repair and its corresponding ownership pin.

The separate #139→ownership-baseline→#134 protected sequence remains independent and must not be treated as cleared by #187. Any reuse of those candidates requires refresh/requalification against current main and the applicable protected-byte policy.

## Research and planning candidates

- **#188** — additive AQ-GOV-001 consensus-authority escalation lab. It assumes unanimous 10/10 agent approval and tests whether existing quarantine/WorkerContract/AttemptGuard boundaries still prevent authority escalation. It is an unaccepted research candidate and does not claim kernel/container/hypervisor/broker escape resistance.
- **#160/#161/#162/#163/#164/#166/#167** — IE-001→IE-007 specification/test-planning branches; no accepted runtime/performance/cost/research claim.
- **#177** — IE-001 prototype candidate; prior evidence remains bound to its candidate head and needs reconciliation/requalification against current main/current IE-001 contract.
- **#152** — Qualification v1 framework candidate; older results must be refreshed before current release claims use them.
- **#191** — automated PR-review workflow candidate; unaccepted and not part of repository governance until merged and qualified.

Merged #168 continues to define normal repository merge control as:

`automated qualification/review appropriate to scope -> exact-head maintainer attestation -> merge`

This is maintainer-reviewed with automated qualification, not independent human assurance.

## Release and research non-claims

The project does **not** yet claim that:

- the historical Controller/provider FAIL is erased by #187;
- #187 establishes every-host/capable-runner M4 qualification;
- #189 is post-merge production-qualified before its exact merged-sha workflows/deployment complete;
- #189 proves Puter SDK/sign-in or live inference works in production until retained post-deploy evidence exists;
- #186 proves heavyweight WebVM reliability on physical iPhone Safari;
- WebVM long-run reliability is acceptable or the historical corruption family is root-caused;
- blank-environment install/recovery qualification is complete;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- #190/#188/#191 are accepted capability;
- #177 has final IE-001 qualification;
- the solo-maintainer model supplies independent human assurance;
- confirmatory live-model evaluation has established the central reliability hypothesis.

## Next gates

1. Observe the first exact-current-main post-#189 workflow/deployment set and retain any first-attempt failure.
2. Verify the production provider helper after the merged #189 Pages deployment: SDK load and sign-in availability must be retained evidence, not inferred from pre-merge CI.
3. Refresh/requalify #190 against current main before integration, then retest provider-session recovery after deployment.
4. Retain a fresh real-account Puter mission on the exact deployed accepted revision before claiming live-provider PASS, or explicitly exclude that claim.
5. Validate the accepted #186 iOS/WebKit fallback on a physical device without turning fallback success into a heavyweight-WebVM claim.
6. Execute true blank-environment install and recovery/host-loss qualification for the exact release artifact.
7. Complete the selected elapsed soak tier with retained first-failure evidence.
8. Continue #120/#126 reliability work and the separate #139→ownership-baseline→#134 protected sequence.
9. Refresh/requalify #152 and #177 before current release/research claims use them.
10. Freeze and run confirmatory R0–R5/degradation/heterogeneous-routing studies only under the stated research protocol.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head workflow output and retained machine-readable artifacts;
3. open qualification/security/reliability issues and explicit release policy;
4. submitted maintainer/protected-byte/ownership-baseline review records;
5. this current-status document;
6. `implementation-status.yaml` for implementation traceability;
7. historical specs/snapshots for design intent, not current qualification claims.
