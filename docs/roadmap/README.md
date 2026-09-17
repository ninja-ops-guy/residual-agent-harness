# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented research/operations surface; exact-current-main `push` qualification is presently mixed because the Python 3.11 Command Station lane is retained **FAIL** |
| Factory M2 worker contracts/runtime | Implemented under `residual/factory/` |
| Factory M3 evidence bus/Station receipts | Implemented; trusted admission remains the authority boundary |
| Factory M4 deterministic integration/scheduler | Implemented; qualification remains exact-revision/environment bound rather than every-host |
| Mission Control/WebVM lifecycle | #159 fresh-overlay recovery, #153 browser acceptance proof, #171/#173 provider transport, #169 local diagnostics, #179 bounded build-output handling and #183 provider-session lifecycle recovery are merged; current-main Pages passes, while physical iPhone/WebKit reliability remains failing/unknown at the runtime boundary and paid/live provider success remains `UNKNOWN` |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Sandbox / red-team | Implemented development surface; host capability determines which kernel isolation paths can be qualified |
| Cluster / distributed execution | Implemented development surface; production guarantees remain narrower than fixtures |
| Lifecycle / side-effect gateway | Implemented deny-by-default controls and deterministic recovery mechanisms |
| Research/reproducibility | Active; live R0–R5 and elapsed soak remain future evidence gates |

Issues **#63** and **#48** are closed. `implementation-status.yaml` records implementation presence and remains current for that purpose.

## Current main

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`**.

Recent material sequence:

1. **#159 merged** — poison remains fenced; failed browser guests recover through a fresh browser-session writable overlay.
2. **#168 merged** — repository governance moved to automated qualification plus exact-head maintainer attestation; this is not independent human assurance.
3. **#153 merged** — WebVM terminal proof/control-unlock acceptance was hardened.
4. **#171/#173 merged** — bounded provider protocol compatibility and explicit `protocol_rejected` classification landed without giving provider/model output acceptance authority.
5. **#169 merged** — local-first privacy-safe diagnostics and sanitized triage bundles landed without changing authoritative guest evidence.
6. **#179 merged** — browser build-only provider output moved to a bounded 8192-token ceiling/default while non-build/source-grounded live mode remained 1536, with fail-closed truncation classification.
7. **#183 merged** — mobile provider-session lifecycle now tolerates bounded timer throttling/tab reload by refreshing valid-message liveness, recovering the private channel from session storage, and restoring an already signed-in Puter session where available. It does not change model-call authority or claim to fix the iPhone/WebVM crash.

The final #183 head `0b520064cb9deff32dc7d1c261dcaf99f3dc2848` completed all observed PR workflows **PASS** and received exact-head maintainer attestation before merge.

Exact merged-main qualification is **not all-green**. Six of seven observed `push` workflows are **PASS**. **Command Station checks** run `35219212073` is retained **FAIL** on attempt 1 because the Python 3.11 full unittest step failed; browser, Docker, Python 3.12 and Python 3.13 jobs passed. The exact failing test/cause remains **UNKNOWN** from retained workflow metadata currently available. **Deploy GitHub Pages** run `35219212133` is **PASS** on attempt 1.

Fresh physical-device evidence from predecessor live `main@250494f2...` reports desktop success while iPhone/WebKit crashes on the heavyweight WebVM path. No retained typed iPhone crash exception/artifact exists for that report, so the internal WebKit failure mechanism remains **UNKNOWN**. The separate provider-session reconnect symptom motivated #183, but post-merge real-device provider-session acceptance has not yet been promoted to `PASS`.

The earlier `main@2b7cb626...` protected M4 `/proc/<pid>/status` observation-race **FAIL** remains retained historical evidence. Later green runs do not prove that protected race fixed.

## Current build order

1. **Triage the exact-current-main Command Station failure without rerunning it away.** Preserve run `35219212073` as `FAIL`; identify the Python 3.11 failing test from retained evidence before assigning root cause or closure.
2. **Refresh the iOS safe-mode candidate onto current main.** PR #182 exact head `dc1e4233f1fc801c2265ad793b5d7d000c2a1473` has all observed technical workflows `PASS`, including dedicated iOS WebKit preflight and Pages, but maintainer approval is `FAIL/BLOCKED` and the branch predates #183. Refresh/requalify it, obtain exact-head attestation, and only after any accepted merge require the first production Pages result plus a physical iPhone retest.
3. **Retest #183's provider-session lifecycle on a physical device.** Treat that result separately from WebVM runtime reliability. A follow-up/reload success does not prove the iPhone WebVM crash fixed.
4. **Re-test the live-provider semantic boundary on an accepted deployed revision.** Historical mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` remains retained `FAIL/BLOCKED`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain `UNKNOWN`. Merged #179 and #183 do not substitute for a fresh real-account mission.
5. **Keep standalone generated-build consistency scoped.** Open #180 remains a narrow unaccepted candidate and now predates the #183 main move; refresh/requalification is required before any current-main claim. It is not a browser-demo blocker.
6. **Resolve the protected M4 observation-race gate without weakening trust boundaries.** PR #139 isolates the repair. Review the protected byte change, deliberately handle the ownership baseline only if accepted, and run fresh qualification after any pin advancement.
7. **Requalify downstream #134 only after the protected sequence where applicable.** A green provider/browser sibling lane is not a substitute for protected-byte closure.
8. **Continue WebVM reliability work.** Keep #120/#126 open. Physical iPhone/WebKit failure, timed-wait evidence, the poison event and older corruption evidence have not been proven to share one cause. Preserve first failures and run retained diagnostics rather than inferring reliability from isolated green deployments or a safe mobile fallback.
9. **Refresh/requalify Qualification v1 (#152).** Older aggregate evidence does not automatically qualify current main. Keep virtual/simulated days separate from elapsed wall-clock soak.
10. **Finish release/recovery qualification.** Exercise true blank-environment install, recovery and retained-evidence procedures. Procedure fixtures and simulations are not production release `PASS`.
11. **Keep IE-001 evidence scoped.** Draft #177 reports 203 focused prototype tests passing, but Q11 genuinely independent current-head technical review remains pending and the branch predates current main. Do not call IE-001 finally qualified or production-integrated.
12. **Freeze the confirmatory live evaluation before outcome access.** Lock workload, task mapping, run identity, model/configuration, verifier policy, evidence path, metrics and analysis choices.
13. **Run fixed-model R0–R5, degradation and heterogeneous-routing studies.** Report raw correctness, acceptance coverage, accepted correctness, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency and throughput.
14. **Run live fault campaigns and staged elapsed soak.** 24-hour → 72-hour → 30-day only after shorter gates are clean.
15. **Promote paper claims only from retained evidence.** Negative, `UNKNOWN`, rejected and failed runs stay in the record.

## Governance note

Merged #168 establishes repository merge control as automated qualification plus exact-head maintainer attestation. Use wording such as **maintainer-reviewed with automated qualification** unless another human actually supplied independent review.

This does not erase claim-specific requirements for independent/third-party security review, research validation, release evidence or protected-byte handling.

## Planning and prototype work

PRs #160–#167 are inference-engineering specifications unless their implementations later land and requalify. Draft **#177** is the IE-001 development-only prototype qualification candidate; it is not production runtime and does not have final Q11 qualification. Draft **#178** is a documentation-only dependency-ordered IE-002→IE-007 implementation backlog and explicitly makes no runtime speedup, token/cost, routing, GPU or paper-facing claims. Draft **#175** is a specification-only OpenViking/context-provider proposal with no runtime dependency or accepted implementation claim. Open **#180** and **#182** are unaccepted candidates whose existing evidence predates the latest main move.

Planning artifacts and prototype-only candidates should not be counted as accepted production capability or used as a reason to change `implementation-status.yaml` by themselves.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md)
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md)
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md)
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md)
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md)

These documents remain useful for lineage, but they do not override current code, exact-commit evidence, retained failures, current governance or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
