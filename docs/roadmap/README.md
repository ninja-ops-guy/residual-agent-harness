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
| Mission Control/WebVM | Integrated through #145/#147; exact current-main browser qualification passes, but long-run reliability and historical root cause remain open |
| Real Puter provider path | Transport/conformance hardening integrated; current-main follow-up #149 is exact-head green but independently unreviewed, and fresh real-account success is not yet retained |
| Frozen evaluation framework | Implemented under `residual/eval/`; live confirmatory results remain future evidence |
| Cluster / distributed / lifecycle / observability | Implemented development surfaces; deployment evidence remains environment-specific |
| Self-maintenance research | Bounded proposal/verification evidence exists; no autonomous merge authority |

Issues #63 and #48 are closed. `implementation-status.yaml` records implementation presence; it must be read separately from qualification, release, provider and research evidence.

## Current main boundary — technically qualified, review-provisional

Current `main` is **`0580c1e53ddb9163d2423d82c0bca846a6d68ba2`**, the merge of PR #147. Its observed automated/browser qualification is **PASS**, but independent technical acceptance remains review-provisional because merged PRs #145 and #147 have no submitted reviews in the retained GitHub review record.

PR #145 integrated a libc-relative polling mitigation for long-lived browser paths after retained diagnostics showed positive Python timed waits failing under WebVM. PR #147 tightened real Puter response transport/conformance and changed the visible default Mission Control model to `openai/gpt-5.4-nano`.

Exact #145 and #147 candidate heads completed their observed applicable PR workflow sets **PASS**. Exact merged current main also passed its observed push qualification set; Pages run `35138502311` passed generated desktop+narrow proof, deployment, published real-guest execution and published narrow Chromium acceptance.

This does not establish independent review, live Puter quality or long-run WebVM reliability. The retained real-account run before #147 remained **FAIL** as `provider_protocol_invalid`, and a successful post-#147 real-account run is not yet retained.

## Current build order

1. **Close the governance enforcement gap.** Issue #144 remains open. Obtain independent post-merge technical review of the current #145/#147 integration, then finish PR #146/platform enforcement so future important merges cannot pass with zero qualifying approvals. #146 itself is currently red and based on older main.
2. **Review the current-main provider-envelope follow-up before new live-provider claims.** PR #149 head `2b4c2d09...` ports the surviving nested `updates.build` guidance from closed-unmerged #143 onto `main@0580c1e5...`. All eight observed applicable exact-head workflows are **PASS**, including Browser VM Demo CI and Pages, but there are zero submitted reviews. Require independent technical acceptance before any integration; green CI is not real-account provider success. After any accepted integration, run and retain a fresh real-account Puter acceptance on the exact deployed revision and preserve `PASS`, `FAIL` or `UNKNOWN`.
3. **Quantify WebVM reliability.** Issues #120/#126 remain open. #145 avoids the known Python timed-wait surface, but historical guest corruption is not root-caused. Run a predefined retained repeated-run campaign before claiming an acceptable failure rate.
4. **Resolve the protected M4 test-race lane.** PR #139 requires genuinely independent exact-head review, deliberate ownership-baseline handling and fresh qualification. Do not advance the protected pin merely to obtain green CI.
5. **Refresh/requalify #134 only after the protected sequence.** Its retained adapter tests and historical partial green evidence do not qualify it on current `main@0580c1e5...`.
6. **Finish refreshed current-main candidates without inheriting historical qualification.** PR #140 is now refreshed at `205257e7...`: Browser VM Demo CI and the six non-Pages repository workflows observed so far are **PASS**, while Pages run `35147236161` remains **IN PROGRESS** and no submitted review is recorded. PR #131 is refreshed at `818af414...`: its six observed non-Pages workflows are **PASS**, while Pages run `35147159269` remains **IN PROGRESS** and no submitted review is recorded. Older-base #118, #115, #93 and other candidates still require refresh/requalification. PR #142 is closed unmerged and superseded by #145; PR #143 is closed unmerged and its surviving unique guidance has moved to #149.
7. **Execute broader release/recovery qualification.** Exercise blank-environment setup and actual recovery without converting rehearsal or simulation into release `PASS`.
8. **Freeze the confirmatory live-evaluation protocol before outcome access.** Lock exact source, workload, model/configuration, evidence path, verifier policy, metrics and analysis.
9. **Run fixed-model R0–R5, degradation and heterogeneous-routing studies.** Preserve all negative, rejected and `UNKNOWN` results.
10. **Run staged live fault and soak campaigns.** 24h → 72h → 30-day only after shorter gates are clean.
11. **Promote paper claims only from retained exact-source evidence.**

## Claim discipline

- `PASS` means the named gate passed for the named revision/environment.
- `FAIL` remains retained evidence; reruns do not erase it.
- `UNKNOWN` means causality, evidence or qualification is unresolved.
- `BLOCKED` means a required capability/gate could not validly execute; it is not `PASS`.
- Green automated provider/browser tests do not imply successful real-account provider inference.
- A merged change with no independent submitted review does not retroactively acquire independent acceptance from CI.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md)
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md)
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md)
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md)
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md)

These documents do not override exact code, current workflow evidence, open issues or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
