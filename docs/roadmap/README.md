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
| Mission Control/WebVM lifecycle | #159 fresh-overlay recovery, #153 browser acceptance proof, #171/#173 bounded provider transport, and #169 privacy-safe local diagnostics are merged; current-main Pages/browser qualification passes, while live paid-provider success remains `UNKNOWN` |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Sandbox / red-team | Implemented development surface; host capability determines which kernel isolation paths can be qualified |
| Cluster / distributed execution | Implemented development surface; production guarantees remain narrower than fixtures |
| Lifecycle / side-effect gateway | Implemented deny-by-default controls and deterministic recovery mechanisms |
| Research/reproducibility | Active; live R0–R5 and elapsed soak remain future evidence gates |

Issues **#63** and **#48** are closed. `implementation-status.yaml` records M2/M3/M4/EVAL implementation presence and remains current for that purpose.

## Current main

Current `main` is **`160c01a1b1933ee10c82dcf30b1674a17f7560ff`**.

Recent material sequence:

1. **#159 merged** — poison remains fenced; a failed Mission Control guest is recovered by rotating to a fresh browser-session writable overlay.
2. **#168 merged** — repository governance changed to solo-maintainer approval with automated qualification plus exact-head maintainer attestation. This is not independent human assurance.
3. **#153 merged** — WebVM terminal proof uses an unambiguous bounded marker and browser acceptance waits for the separate post-run control-unlock transition.
4. **#171/#173 merged** — bounded provider-protocol compatibility remains separately counted, normal Puter tool transport preserves original harness messages, and `protocol_rejected` separates provider transport success from RESIDUAL envelope rejection.
5. **#169 merged** — local-first privacy-safe diagnostic telemetry and sanitized triage bundles were added without changing authoritative guest evidence, provider routing, mission authority or qualification semantics.

The final #169 head `fb767dc9682533a6092eb36de783e15a3bd47c13` completed exact-head qualification and received an exact-head maintainer attestation before merge.

All seven observed current-main `push` workflows completed **PASS**. Pages/WebVM run `35182396521` passed on attempt 1 through provider/publication contracts, generated desktop+narrow proof, deployment, published real-guest execution, published narrow-Chromium acceptance and retained live-acceptance proof. This is exact-revision automated/browser evidence, not a live paid-provider/model result.

The prior `main@2b7cb626...` Controller/provider **FAIL** on the protected M4 `/proc/<pid>/status` observation race remains retained historical evidence. A later green run does not prove the race fixed.

## Current build order

1. **Repair the live build-provider boundary without broadening claims.** Fresh real iPhone/WebKit mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice but both counted calls ended `provider_protocol_invalid`; no candidate crossed the protocol boundary and semantic verification did not run. Treat the result as retained `FAIL/BLOCKED`; candidate correctness remains `UNKNOWN`.
2. **Refresh/requalify #176 on current main.** #176 proposes a build-only output ceiling/default of 8192 while keeping non-build/source-grounded live mode at 1536 and failing closed on provider truncation. Its current head is diverged from current main; prior CI/attestation are historical. After any accepted merge, require post-merge Pages proof plus a new real iPhone/WebKit mission before claiming the live path fixed.
3. **Resolve the protected M4 observation-race gate without weakening trust boundaries.** PR #139 isolates the repair. Review the protected byte change, deliberately handle the ownership baseline only if accepted, and run fresh qualification after any pin advancement.
4. **Requalify downstream provider-adapter work only after the protected sequence where applicable.** #134 remains downstream of #139 for that protected dependency.
5. **Continue WebVM reliability work.** Keep #120/#126 open. The positive-duration Python timed-wait boundary, older runtime corruption and the production poisoned-guest event have not been proven to share one cause. Run a defined repeated-run campaign and preserve failures rather than inferring reliability from isolated green deployments.
6. **Refresh/requalify Qualification v1 (#152).** Older aggregate evidence does not automatically qualify current main. Keep virtual/simulated days separate from elapsed wall-clock soak.
7. **Finish release/recovery qualification.** Exercise true blank-environment install, recovery and retained-evidence procedures. Procedure fixtures and simulations are not production release `PASS`.
8. **Keep IE-001 evidence scoped.** Draft #177 reports 203 focused prototype tests passing plus green exact-head repository qualification/governance on its branch, but Q11 genuinely independent current-head technical review remains pending and the branch predates current main. Do not call IE-001 finally qualified or production-integrated.
9. **Freeze the confirmatory live evaluation before outcome access.** Lock workload, task mapping, run identity, model/configuration, verifier policy, evidence path, metrics and analysis choices.
10. **Run fixed-model R0–R5, degradation and heterogeneous-routing studies.** Report raw correctness, acceptance coverage, accepted correctness, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency and throughput.
11. **Run live fault campaigns and staged elapsed soak.** 24-hour → 72-hour → 30-day only after shorter gates are clean.
12. **Promote paper claims only from retained evidence.** Negative, `UNKNOWN`, rejected and failed runs stay in the record.

## Governance note

Merged #168 supersedes #146's proposed generic repository-wide independent-human gate. The repository merge-control model is automated qualification plus exact-head maintainer attestation. Use wording such as **maintainer-reviewed with automated qualification** unless another human actually supplied independent review.

This does not erase claim-specific requirements for independent/third-party security review, research validation, release evidence or protected-byte handling.

## Planning and prototype work

PRs #160–#167 are inference-engineering specifications unless their implementations later land and requalify. Draft **#177** is the IE-001 development-only prototype qualification candidate; it is not production runtime and does not have final Q11 qualification. Draft **#178** is a documentation-only dependency-ordered IE-002→IE-007 implementation backlog and explicitly makes no runtime speedup, token/cost, routing, GPU or paper-facing claims. Draft **#175** is a specification-only OpenViking/context-provider proposal with no runtime dependency or accepted implementation claim.

Planning artifacts and prototype-only candidates should not be counted as accepted production capability or used as a reason to change `implementation-status.yaml` by themselves.

## Historical implementation material

Useful background remains in:

- [DELEGATION.md](DELEGATION.md)
- [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md)
- [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md)
- [TRACK-1-IMPLEMENTATION.md](TRACK-1-IMPLEMENTATION.md)
- [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md)

These documents remain useful for lineage, but they do not override current code, exact-commit evidence, retained failures, current governance or [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md).
