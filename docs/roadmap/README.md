# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; merged #194 retains/reopens completed generated-spec drafts |
| Native interactive setup | Merged #193 adds `setup.sh` for Python 3.11+ host setup; convenience path only, not blank-environment qualification |
| Factory M2/M3/M4 | Implemented; exact-revision/environment qualification remains narrower than implementation presence |
| Mission Control/WebVM lifecycle | Recovery/provider/publication/fallback improvements are merged; #133 adds runtime discriminators and narrows one CPython timed-wait symptom, but long-run reliability/root cause remain unqualified |
| iOS/WebKit release behavior | #186 fallback routes the unsupported/unqualified heavy-WebVM iOS profile to the walkthrough; physical-device validation remains open |
| Provider helper publication | #189 boundary repair is accepted; successful paid/live provider execution still requires retained exact-revision evidence |
| AQ-GOV-001 authority lab | #188 is accepted as bounded adversarial test/research apparatus; not a kernel/container/hypervisor/broker escape proof |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| #132 self-hosting/research-bundle tooling | Historical merged evidence only; implementation/workflow/tests/docs were removed by #133 and are absent from current main |
| Release/recovery/soak | True blank-environment install, recovery/host-loss evidence and selected elapsed soak remain gates |

`implementation-status.yaml` records implementation presence for its tracked requirement families. It is not a release-qualification manifest, and #193 does not change a tracked requirement-family state.

## Accepted main

Current `main` is **`699e2869e294fe157b4bfd73a272057683a2f7e0`**.

Material accepted sequence relevant to the current build state:

1. **#188 merged** — AQ-GOV-001 consensus-authority escalation lab. Ten-of-ten worker approval is deliberately assumed; existing host-side controls must still deny the tested forbidden actions. Scope is bounded to the software paths exercised.
2. **#194 merged** — completed generated-spec results remain visible/clickable and can repopulate Mission Intake after the initiating watcher disappears.
3. **#133 merged** — WebVM runtime discriminator workflows/scripts. Retained evidence narrows one failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`, while direct libc wait controls continue beyond that boundary. Exact lower-level cause remains **UNKNOWN**.
4. **#133 also removed #132's accepted self-hosting/research-bundle surface.** Treat #132 as historical evidence, not current capability, until an explicit retirement/restoration decision is made.
5. **#192 merged stale current-state documentation** based on an earlier accepted-main snapshot. This changed prose, not implementation authority; the affected docs require correction to the actual current state.
6. **#193 merged** — interactive native setup helper. It selects Python 3.11+, creates/reuses a venv, installs the checkout, exports PATH, optionally installs a no-argument `residual` serve macro and exposes the local Station URL.

## Qualification boundary

All seven ordinary first-attempt `push` workflows on exact predecessor `main@b3f00af...` completed **PASS**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, Command Station and Pages/deployment.

The exact #193 candidate head `d97104958a235d9439fd3c36cc72221ba454b3cc` completed the observed Control Plane, Factory ownership, clean-install, Controller/provider, measured-binding, Command Station and maintainer-approval workflows **PASS** before merge.

Exact `main@699e286...` post-merge qualification is a separate evidence set. It remains **PENDING** until applicable runs complete; predecessor/candidate PASS is not silently inherited.

Required interpretation:

- accepted #193 bytes on current main: **PASS / merged**;
- predecessor-main named workflows: **PASS within their exact scopes**;
- #193 exact candidate-head named workflows: **PASS within their exact scopes**;
- exact current-main post-merge workflow set: **PENDING** at this snapshot;
- WebVM timed-wait lower-level root cause: **UNKNOWN**;
- long-run WebVM reliability: **UNKNOWN / unqualified**;
- paid/live provider semantic success: **UNKNOWN** until retained exact-revision candidate→verifier→receipt evidence exists;
- capable-runner/every-host M4 qualification: **not established by hosted/prerequisite CI**;
- true blank-environment install: **not established by #193**.

## Current build order

1. **Finish exact-current-main post-#193 qualification.** Preserve any first failure; do not treat candidate-head or predecessor-main PASS as merged-sha evidence.
2. **Resolve the #133/#132 integration discrepancy.** Decide explicitly whether removal of #132 self-hosting/research-bundle tooling was intended retirement or an integration regression. Any restoration should be a focused reviewed implementation change, not a documentation rewrite.
3. **Continue #120/#126 WebVM reliability work from the #133 discriminators.** The shared CPython timeout/wait symptom is narrowed, but the exact ABI/emulation cause, relationship to older corruption and recurrence rate remain unknown.
4. **Refresh/requalify #190.** Its provider-channel recovery candidate requires current-tree reconciliation before integration; post-merge production retest remains separate if later accepted.
5. **Retest the live-provider semantic boundary on the exact deployed accepted revision.** Historical mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` remains `FAIL/BLOCKED`; paid/live success stays UNKNOWN until a candidate crosses protocol validation and normal verifier/receipt handling.
6. **Physically validate the accepted #186 fallback.** Do not broaden fallback success into a heavyweight-WebVM reliability claim.
7. **Execute true blank-environment installation and recovery/host-loss qualification for the exact release artifact.** #193 is a convenience path for a host that already has Python 3.11+.
8. **Complete the selected elapsed-soak tier.** Simulation is not elapsed wall-clock soak.
9. **Keep #139→ownership-baseline→fresh-qualification→#134 independent.** Unrelated merges do not clear that protected sequence.
10. **Refresh/requalify #152 and #177 before current release/research claims use them.**
11. **Freeze and run confirmatory research only after operational claims are bounded.**

## Planning and prototype work

- **#188** — accepted/on main as bounded AQ-GOV-001 adversarial apparatus.
- **#194** — accepted/on main as the completed-draft visibility/reopen repair.
- **#133** — accepted/on main as diagnostic tooling plus the current file-state change described above; diagnostic FAILs and UNKNOWN root cause remain visible.
- **#193** — accepted/on main as interactive setup convenience; not blank-environment release evidence.
- **#190** — open provider-channel recovery candidate; refresh/requalification required as applicable after current-main movement.
- **#152** — Qualification v1 framework candidate; refresh required before current release use.
- **#177** — IE-001 prototype candidate; reconcile/refresh before final qualification.
- **#160/#161/#162/#163/#164/#166/#167** — inference-engineering specifications/planning; no accepted production/performance/research claim merely from the specs.
- **#191** — closed unmerged; its automated PR-review workflow is not accepted governance.
- **#132** — historical self-hosting/research-bundle experiment; current implementation surface is absent after #133.

Planning artifacts and prototype-only candidates must not be counted as accepted production capability or used as a reason to change `implementation-status.yaml` by themselves.

## Release evidence rule

A merge onto main establishes that the merged bytes are part of the repository. It does not automatically establish every release, reliability, security or research claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, recovery, soak, or the intent behind a removed accepted feature must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN` and `BLOCKED` results remain visible even when later revisions pass.
