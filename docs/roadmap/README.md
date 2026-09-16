# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

Current `main` contains the core harness, Command Station, Factory M2/M3/M4, evaluation infrastructure, sandbox/red-team tooling, cluster execution, orchestration, lifecycle/gateway controls, observability, product surfaces, WebVM/Mission Control and research/reproducibility machinery.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented research/operations surface; deployment-specific production qualification still applies |
| Factory M2 worker contracts/runtime | Implemented under `residual/factory/` |
| Factory M3 evidence bus/Station receipts | Implemented; trusted consumption/admission is the authority boundary |
| Factory M4 deterministic integration/scheduler | Implemented and capable-runner qualified on named environments; every-host qualification is not claimed |
| Mission Control/WebVM | Integrated through #151; exact current-main automated/browser qualification passes, but independent review and long-run reliability remain open |
| Real Puter provider path | Transport/live-pipeline hardening integrated; successful paid/live-provider acceptance on exact current main is still `UNKNOWN` |
| Frozen evaluation framework | Implemented under `residual/eval/`; live confirmatory results remain future evidence |
| Cluster / distributed / lifecycle / observability | Implemented development surfaces; deployment evidence remains environment-specific |
| Self-maintenance research | Bounded proposal/verification evidence exists; no autonomous merge authority |

Issues #63 and #48 are closed. `implementation-status.yaml` records implementation presence; it must be read separately from qualification, release, provider and research evidence.

## Current main boundary — technically qualified, review-provisional

Current `main` is **`f2d58e779ad589fe1d08842c9efc40ec5214a213`**, tree **`c62cf2a5d8c4234edcd7e53e0faa8edeb94a1571`**, the merge of PR #151.

All seven observed main-push workflows are **PASS** on that exact revision. M4 run `35149837820` used the real namespace-isolated path with **142 tests + 84 subtests, zero skips**. Pages run `35149837756` passed first-attempt generated and published desktop+narrow acceptance; retained proof artifact `10468668615` is hash-bound.

GitHub records zero submitted reviews for #151, so the revision remains **review-provisional**. The provider portion of the post-merge browser proof used the SDK test double with `cloud_inference: NOT_RUN`; a successful paid/live Puter run on exact current main is **UNKNOWN / not retained**.

## Current build order

1. **Close the independent-review governance gap.** Issue #144 remains open. Retain a genuinely independent post-merge technical review of the #151 merged surface. PR #146 is now rebuilt on exact current main and implements the fail-closed repository check; after independent acceptance, the active ruleset still needs a maintainer change so approving review count is at least one and the new status is required.
2. **Obtain fresh real-account provider evidence.** Run Puter against exact deployed `main@f2d58e77...`. Automated/provider-browser `PASS` is test-double/contract evidence only. Preserve live `PASS`, `FAIL` or `UNKNOWN` exactly.
3. **Finish current-main WebVM acceptance repair #153.** It consolidates the closed-unmerged #140/#150 repairs into four harness files on current main. At the latest snapshot Factory ownership and Control Plane pass, Browser VM Demo/Pages are in progress, and several workflows are queued. Require complete exact-head qualification plus genuinely independent review before integration. Then refresh/requalify #89; its retained historical Pages failure remains authoritative.
4. **Continue Qualification v1 #152 without promoting partial evidence.** The draft adds a fail-closed qualification manifest, stateful exploration, DSM/fault evidence, mutation canaries, exact-wheel qualification, multi-browser journeys and soak/canary tooling. Its current workflow set is partial/in progress. Virtual-day stress is not elapsed soak; planned 24h/72h/30d workflows are not evidence until actually completed.
5. **Quantify WebVM reliability.** Issues #120/#126 remain open. #145 avoids the known process-local Python timed-wait trigger, but the historical corruption family is not root-caused. Run a predefined retained repeated-run campaign before claiming an acceptable recurrence rate.
6. **Resolve the protected M4 test-race lane.** PR #139 requires genuinely independent exact-head review, deliberate ownership-baseline handling and fresh qualification. Do not advance the protected pin merely to obtain green CI.
7. **Refresh/requalify #134 only after the protected sequence.** Its historical partial evidence does not qualify it on current main.
8. **Refresh older integration candidates after #151.** #118, #115, #131 and #149 were last qualified on pre-#151 main; those exact-head results remain historical only. #93 remains red because of its retained runtime-journal concurrency failure and protected dependency.
9. **Execute broader release/recovery qualification.** Exercise blank-environment setup and actual recovery without converting rehearsal or simulation into release `PASS`.
10. **Freeze confirmatory evaluation before outcome access.** Lock exact source, workload, model/configuration, evidence path, verifier policy, metrics and analysis.
11. **Run fixed-model R0–R5, degradation and heterogeneous-routing studies.** Preserve negative, rejected and `UNKNOWN` results.
12. **Run staged live fault and soak campaigns.** 24h → 72h → 30-day only after shorter gates are clean.
13. **Promote paper claims only from retained exact-source evidence.**

## Claim discipline

- `PASS` means the named gate passed for the named revision/environment.
- `FAIL` remains retained evidence; reruns do not erase it.
- `UNKNOWN` means causality, evidence or qualification is unresolved.
- `BLOCKED` means a required capability/gate could not validly execute; it is not `PASS`.
- Green automated provider/browser tests do not imply successful real-account provider inference.
- A merged change with no independent submitted review does not retroactively acquire independent acceptance from CI.
- Candidate qualification before a later `main` merge remains historical until the candidate is refreshed/requalified.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md)
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md)
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md)
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md)
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md)

These documents do not override exact code, current workflow evidence, open issues or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
