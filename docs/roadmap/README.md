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
| Mission Control/WebVM | Integrated through #156; exact current-main automated/browser qualification passes, but fresh post-#156 iPhone/WebKit evidence retains an end-to-end poisoned-guest **FAIL** and long-run reliability remains open |
| Real Puter provider path | #156 repairs the earlier worker-envelope failure; fresh production evidence reached `Provider connected` but no valid candidate completed because the guest was poisoned. Successful paid/live candidate execution remains `UNKNOWN` |
| Poisoned-guest recovery | #159 exact head is technically green for browser/guest recovery but `BLOCKED` on independent review; #158 exact head is `FAIL` because durable-poison regressions failed |
| Frozen evaluation framework | Implemented under `residual/eval/`; live confirmatory results remain future evidence |
| Cluster / distributed / lifecycle / observability | Implemented development surfaces; deployment evidence remains environment-specific |
| Self-maintenance research | Bounded proposal/verification evidence exists; no autonomous merge authority |

Issues #63 and #48 are closed. `implementation-status.yaml` records implementation presence; it must be read separately from qualification, release, provider and research evidence.

## Current main boundary — technically qualified, review-provisional

Current `main` is **`f6f9bad84caccf68c7ab35e5788e756d12c55fb7`**, tree **`9991788c5d59b8ccd3b18b10ad0d4a46098305df`**, the merge of PR #156.

All seven observed main-push workflows are **PASS** on that exact revision. The M4 prerequisite/qualification workflow passed its fail-closed capability and zero-skip gate. Pages run `35158939226` passed on attempt 1 through generated desktop+narrow proof, deployment, published real-guest execution and published narrow-Chromium acceptance.

GitHub records zero submitted reviews for #156, so the revision remains **review-provisional**.

The provider/recovery evidence is now more specific than the earlier snapshot: pre-#156 real-account provider-envelope evidence remains **FAIL** as `provider_protocol_invalid`; fresh post-#156 iPhone/WebKit evidence reaches **`Provider connected`** but then records **`RESIDUAL_WORKER_POISONED`** with Mission Control stuck at **`GUEST STARTING`**. The public demo attempt is therefore end-to-end **FAIL** at the guest-recovery/product boundary. Successful paid/live candidate execution remains **UNKNOWN** because no valid candidate completed the normal verifier path. The lower-level poison cause remains **UNKNOWN**.

## Current build order

1. **Review the technically green whole-guest poison recovery, PR #159.** Exact head `5c33f31d234e3be315a052109fe270d3b70276c5` has all eight observed applicable workflows **PASS**, including Browser VM Demo CI and generated desktop+narrow Pages proof. The browser proof deliberately recreates the durable poison boundary, requires `GUEST FAILED · RESTART REQUIRED`, rotates to a fresh browser-session writable overlay, proves poison/PID/control/busy/active-lock state does not carry into the replacement guest, then completes a real local repository audit. Cloud inference remains a test double. The only submitted review is an owner `COMMENTED` handoff explicitly marked not independent acceptance, so #159 is **BLOCKED** until a genuinely independent exact-head reviewer approves it. If accepted and merged, require first-attempt production Pages and a fresh real-account iPhone/WebKit mission before claiming the public demo fixed.
2. **Preserve PR #158 as exact-head FAIL unless it is materially revised.** Head `ac637711...` has clean-install, measured-binding, ownership, Control Plane and Browser VM Demo CI green, but Controller/provider contracts, Command Station and Pages are **FAIL**. The authoritative Python 3.11 run retains two failures because durable poison was removed where the existing recovery contract requires it to remain. Do not waive these failures or merge from partial green evidence.
3. **Close the independent-review governance gap.** Issue #144 remains open. Retain a genuinely independent post-merge technical review of the #156 merged surface. PR #146 is at `c416d408149408ff8668a48d6e73eb1f3bf6347e`; ordinary workflows and its 15 policy regressions pass, while the live `independent-review` gate correctly reports **BLOCKED** because no qualifying independent current-head human approval exists. After accepted integration, the active ruleset still needs a maintainer change so approving review count is at least one and the new status is required.
4. **Obtain independent acceptance for technically qualified WebVM harness repair #153.** It consolidates the closed-unmerged #140/#150 repairs and is based on exact current main at `35cbf2ba060bc04aabb6cfd10fbf90dc8dbccb77`. All eight observed applicable exact-head workflows are **PASS**, including Browser VM Demo CI and Pages/WebVM. Require a genuinely independent current-head approval before integration, then refresh/requalify #89; its retained historical Pages failure remains authoritative.
5. **Refresh/requalify Qualification v1 #152.** The framework adds fail-closed qualification manifests, stateful exploration, DSM/fault evidence, mutation canaries, exact-wheel qualification, multi-browser journeys and soak/canary tooling. Its pre-#156 results are historical only. Virtual-day stress is not elapsed soak; planned 24h/72h/30d workflows are not evidence until actually completed.
6. **Quantify WebVM reliability.** Issues #120/#126 remain open. #145 avoids the known process-local Python timed-wait trigger, but the historical corruption family is not root-caused, and the fresh poisoned-guest production failure adds a separate unresolved reliability observation. Their relationship remains `UNKNOWN`. Run a predefined retained repeated-run campaign before claiming an acceptable recurrence rate.
7. **Resolve the protected M4 test-race lane.** PR #139 requires genuinely independent exact-head review, deliberate ownership-baseline handling and fresh qualification. Do not advance the protected pin merely to obtain green CI.
8. **Refresh/requalify #134 only after the protected sequence.** Its historical partial evidence does not qualify it on current main.
9. **Independently review other refreshed integration candidates.** #118 `ee81051220c616f8a605c948820d972177e19801`, #115 `27e6e3b790d950ad1e8dd3603569f2eb5090ada4`, and #131 `0094dd4c27231f8c4f71161b9a82770a27c7aa7b` have applicable exact-head workflows green but remain blocked on genuine independent acceptance. #115 remains procedure/simulation evidence rather than elapsed soak; #131 stays separate. #93 remains red because of its retained runtime-journal concurrency failure and protected dependency.
10. **Execute broader release/recovery qualification.** Exercise blank-environment setup and actual recovery without converting rehearsal or simulation into release `PASS`.
11. **Freeze confirmatory evaluation before outcome access.** Lock exact source, workload, model/configuration, evidence path, verifier policy, metrics and analysis.
12. **Run fixed-model R0–R5, degradation and heterogeneous-routing studies.** Preserve negative, rejected and `UNKNOWN` results.
13. **Run staged live fault and soak campaigns.** 24h → 72h → 30-day only after shorter gates are clean.
14. **Promote paper claims only from retained exact-source evidence.**

## Claim discipline

- `PASS` means the named gate passed for the named revision/environment.
- `FAIL` remains retained evidence; later repairs or reruns do not erase it.
- `UNKNOWN` means causality, evidence or qualification is unresolved.
- `BLOCKED` means a required capability/gate could not validly execute; it is not `PASS`.
- A connected provider is not proof that a live candidate completed or passed verification.
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
