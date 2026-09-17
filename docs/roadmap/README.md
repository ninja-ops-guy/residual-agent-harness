# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented research/operations surface; deployment-specific production qualification still applies |
| Factory M2 worker contracts/runtime | Implemented under `residual/factory/` |
| Factory M3 evidence bus/Station receipts | Implemented; trusted admission remains the authority boundary |
| Factory M4 deterministic integration/scheduler | Implemented; qualification remains exact-revision/environment bound rather than every-host |
| Mission Control/WebVM lifecycle | #159 fresh-overlay poisoned-guest recovery and #153 browser acceptance proof are merged; current-main Pages passes, but live paid-provider success remains `UNKNOWN` and reliability issues remain open |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Sandbox / red-team | Implemented development surface; host capability determines which kernel isolation paths can be qualified |
| Cluster / distributed execution | Implemented development surface; production guarantees remain narrower than fixtures |
| Lifecycle / side-effect gateway | Implemented deny-by-default controls and deterministic recovery mechanisms |
| Research/reproducibility | Active; live R0–R5 and elapsed soak remain future evidence gates |

Issues **#63** and **#48** are closed. `implementation-status.yaml` records M2/M3/M4/EVAL implementation presence and remains current for that purpose.

## Current main

Current `main` is **`2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`**.

The recent sequence is:

1. **#159 merged** — poison remains fenced; a failed Mission Control guest is recovered by rotating to a fresh browser-session writable overlay.
2. **#168 merged** — repository governance changed to solo-maintainer approval with automated qualification plus exact-head maintainer attestation. This is not independent human assurance.
3. **#153 merged** — WebVM terminal proof now uses an unambiguous bounded marker and browser acceptance waits for the separate post-run control-unlock transition.

The final #153 candidate was green for its applicable exact-head workflows and had the required maintainer attestation. The merged `main` revision is nevertheless **not fully green**: Pages run `35172926305` is **PASS**, while Controller/provider run `35172926291` is **FAIL** in Python 3.12 because the protected M4 `/proc/<pid>/status` observation race raised `FileNotFoundError`. Preserve that first observed main failure.

## Current build order

1. **Resolve the protected M4 observation-race gate without weakening trust boundaries.** Current-main Controller/provider CI is red on `test_timeout_kills_process_group_not_only_parent`. PR #139 isolates the protected repair. Review the protected byte change, deliberately handle the ownership baseline only if accepted, and run fresh qualification after any pin advancement. Do not change the baseline merely to make CI green.
2. **Requalify downstream provider-adapter work only after the protected sequence.** #134 remains downstream of #139. A passing browser/provider sibling lane cannot substitute for a red full-workflow qualification.
3. **Obtain fresh real-account production evidence on the merged browser surface.** #159 now provides a supported fresh-overlay restart and #153 repairs the retained narrow-browser proof parser defect. Current-main Pages is green, but successful paid/live Puter execution on real iPhone/WebKit remains `UNKNOWN` until a retained mission completes the normal verifier/receipt path.
4. **Continue WebVM reliability work.** Keep #120/#126 open. The historical positive-duration Python timed-wait boundary, older runtime corruption and the production poisoned-guest event have not been proven to share one cause. Run a defined repeated-run campaign and preserve failures rather than inferring reliability from isolated green deployments.
5. **Refresh/requalify Qualification v1 (#152).** Its older aggregate evidence does not automatically qualify current main. Keep virtual/simulated days separate from elapsed wall-clock soak.
6. **Finish release/recovery qualification.** Exercise true blank-environment install, recovery and retained-evidence procedures. Procedure fixtures and simulations are not production release `PASS`.
7. **Freeze the confirmatory live evaluation before outcome access.** Lock workload, task mapping, run identity, model/configuration, verifier policy, evidence path, metrics and analysis choices.
8. **Run fixed-model R0–R5.** Measure raw correctness, acceptance coverage, accepted correctness, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency and throughput.
9. **Run degradation and heterogeneous-routing studies.** Test whether weaker/cheaper workers can contribute safely under the same acceptance boundary.
10. **Run live fault campaigns and staged elapsed soak.** 24-hour → 72-hour → 30-day only after shorter gates are clean.
11. **Promote paper claims only from retained evidence.** Negative, `UNKNOWN`, rejected and failed runs stay in the record.

## Governance note

Merged #168 supersedes #146's proposed generic repository-wide independent-human gate. The repository merge-control model is now automated qualification plus exact-head maintainer attestation. Use wording such as **maintainer-reviewed with automated qualification** unless another human actually supplied independent review.

This does not erase claim-specific requirements for independent/third-party security review, research validation, release evidence or protected-byte handling.

## Planning-only inference work

PRs #160–#167 are inference-engineering proposals/specifications unless their implementations later land and requalify. They should not be counted as implemented capability, benchmark evidence or a reason to change `implementation-status.yaml` today.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md)
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md)
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md)
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md)
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md)

These documents remain useful for lineage, but they do not override current code, exact-commit evidence, retained failures, current governance or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
