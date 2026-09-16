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
| Mission Control/WebVM | Integrated through #156; exact current-main automated/browser qualification passes, but independent review and long-run reliability remain open |
| Real Puter provider path | #156 repairs worker-envelope conformance; successful paid/live acceptance on exact current main is still `UNKNOWN` |
| Frozen evaluation framework | Implemented under `residual/eval/`; live confirmatory results remain future evidence |
| Cluster / distributed / lifecycle / observability | Implemented development surfaces; deployment evidence remains environment-specific |
| Self-maintenance research | Bounded proposal/verification evidence exists; no autonomous merge authority |

Issues #63 and #48 are closed. `implementation-status.yaml` records implementation presence; it must be read separately from qualification, release, provider and research evidence.

## Current main boundary — technically qualified, review-provisional

Current `main` is **`f6f9bad84caccf68c7ab35e5788e756d12c55fb7`**, tree **`9991788c5d59b8ccd3b18b10ad0d4a46098305df`**, the merge of PR #156.

All seven observed main-push workflows are **PASS** on that exact revision. The M4 prerequisite/qualification workflow passed its fail-closed capability and zero-skip gate. Pages run `35158939226` passed on attempt 1 through generated desktop+narrow proof, deployment, published real-guest execution and published narrow-Chromium acceptance.

GitHub records zero submitted reviews for #156, so the revision remains **review-provisional**. The latest retained real-account provider evidence before #156 remains **FAIL** as `provider_protocol_invalid`; a successful paid/live Puter run on exact current main is **UNKNOWN / not retained**.

## Current build order

1. **Close the independent-review governance gap.** Issue #144 remains open. Retain a genuinely independent post-merge technical review of the #156 merged surface. PR #146 is refreshed onto current main at `c416d408149408ff8668a48d6e73eb1f3bf6347e`; fresh exact-head qualification and independent write-authorized acceptance remain required. After integration, the active ruleset still needs a maintainer change so approving review count is at least one and the new status is required.
2. **Obtain fresh real-account provider evidence.** Run Puter against exact deployed `main@f6f9bad8...`. Automated/provider-browser `PASS` is contract/transport evidence only. Preserve live `PASS`, `FAIL` or `UNKNOWN` exactly.
3. **Qualify refreshed WebVM acceptance repair #153.** It consolidates the closed-unmerged #140/#150 repairs and is now based on exact current main at `35cbf2ba060bc04aabb6cfd10fbf90dc8dbccb77`. Historical exact-head results remain bound to the superseded head. Require fresh current-head qualification plus genuinely independent review before integration, then refresh/requalify #89; its retained historical Pages failure remains authoritative.
4. **Refresh/requalify Qualification v1 #152.** The framework adds fail-closed qualification manifests, stateful exploration, DSM/fault evidence, mutation canaries, exact-wheel qualification, multi-browser journeys and soak/canary tooling. Its pre-#156 results are historical only. Virtual-day stress is not elapsed soak; planned 24h/72h/30d workflows are not evidence until actually completed.
5. **Quantify WebVM reliability.** Issues #120/#126 remain open. #145 avoids the known process-local Python timed-wait trigger, but the historical corruption family is not root-caused. Run a predefined retained repeated-run campaign before claiming an acceptable recurrence rate.
6. **Resolve the protected M4 test-race lane.** PR #139 requires genuinely independent exact-head review, deliberate ownership-baseline handling and fresh qualification. Do not advance the protected pin merely to obtain green CI.
7. **Refresh/requalify #134 only after the protected sequence.** Its historical partial evidence does not qualify it on current main.
8. **Refresh older integration candidates after #156.** #118, #115, #131 and other lanes retain only revision-bound historical evidence until refreshed. #93 remains red because of its retained runtime-journal concurrency failure and protected dependency.
9. **Execute broader release/recovery qualification.** Exercise blank-environment setup and actual recovery without converting rehearsal or simulation into release `PASS`.
10. **Freeze confirmatory evaluation before outcome access.** Lock exact source, workload, model/configuration, evidence path, verifier policy, metrics and analysis.
11. **Run fixed-model R0–R5, degradation and heterogeneous-routing studies.** Preserve negative, rejected and `UNKNOWN` results.
12. **Run staged live fault and soak campaigns.** 24h → 72h → 30-day only after shorter gates are clean.
13. **Promote paper claims only from retained exact-source evidence.**

## Claim discipline

- `PASS` means the named gate passed for the named revision/environment.
- `FAIL` remains retained evidence; later repairs or reruns do not erase it.
- `UNKNOWN` means causality, evidence or qualification is unresolved.
- `BLOCKED` means a required capability/gate could not validly execute; it is not `PASS`.
- Green automated provider/browser tests do not imply successful real-account provider inference.
- A merged change with no independent submitted review does not retroactively acquire independent acceptance from CI.
- Candidate qualification before a later `main` merge remains historical until the candidate is refreshed/requalified.
- Protected ownership baselines and qualification anchors are deliberate trust-boundary decisions, not CI-green switches.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md)
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md)
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md)
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md)
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md)

These documents do not override exact code, current workflow evidence, open issues or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
