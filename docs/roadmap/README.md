# RESIDUAL roadmap — current build state

> **Current-state entry point:** [../CURRENT_STATUS.md](../CURRENT_STATUS.md)

The documents under [`source/`](source/) preserve earlier design generations and are historical input unless a newer reconciliation says otherwise. Checkmarks in those source documents mean **specified/documented**, not automatically implemented or qualified on the current tree.

## Current capability map

| Capability | Current status |
| --- | --- |
| Core harness / verifier / receipts / residual delegation | Implemented and covered by the established test corpus |
| Command Station | Implemented; merged #194 retains/reopens completed generated-spec drafts |
| Native interactive setup | Merged #193 adds `setup.sh` for Python 3.11+ host setup; convenience path only, not blank-environment qualification. #200 proposes safer persistent/local defaults, is unaccepted, and now has all observed technical exact-head workflows PASS with maintainer attestation still BLOCKED |
| Factory M2/M3/M4 | Implemented; exact-revision/environment qualification remains narrower than implementation presence |
| Mission Control/WebVM lifecycle | Recovery/provider/publication/fallback improvements are merged; #133 adds runtime discriminators and narrows one CPython timed-wait symptom, but long-run reliability/root cause remain unqualified |
| iOS/WebKit release behavior | #186 fallback routes the unsupported/unqualified heavy-WebVM iOS profile to the walkthrough; physical-device validation remains open |
| Provider helper publication | #189 boundary repair is accepted; successful paid/live provider execution still requires retained exact-revision evidence |
| AQ-GOV-001 authority lab | #188 is accepted as bounded adversarial test/research apparatus; not a kernel/container/hypervisor/broker escape proof |
| Frozen evaluation framework | Implemented research apparatus; CI binding is not confirmatory live-model evidence |
| Development local-model evidence | #202 retained one simple local-model mission PASS on historical head `fee21d...`, followed by a later heterogeneous DAG FAIL on head `6b30125...`; #203 retained a bounded M6 self-host experiment FAIL. These are development experiments, not confirmatory R0–R5 results |
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

No later implementation PR has merged onto main at this snapshot. #200, #202 and #203 remain unaccepted/open experiment or hardening work.

## Qualification boundary

All seven ordinary first-attempt `push` workflows on exact predecessor `main@b3f00af...` completed **PASS**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, Command Station and Pages/deployment.

The exact #193 candidate head `d97104958a235d9439fd3c36cc72221ba454b3cc` completed the observed Control Plane, Factory ownership, clean-install, Controller/provider, measured-binding, Command Station and maintainer-approval workflows **PASS** before merge.

On exact current `main@699e286...`, the six observed applicable ordinary post-#193 `push` qualification workflows completed **PASS on attempt 1**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider and Command Station. No Pages/deployment run bound to this exact SHA was observed in the retained run set, so this is deliberately not described as a seven-workflow PASS.

Required interpretation:

- accepted #193 bytes on current main: **PASS / merged**;
- predecessor-main seven named workflows: **PASS within their exact scopes**;
- #193 exact candidate-head named workflows: **PASS within their exact scopes**;
- exact current-main six observed applicable named workflows: **PASS within their exact scopes**;
- exact current-main Pages/deployment: **UNKNOWN / not observed in the retained exact-SHA run set**;
- WebVM timed-wait lower-level root cause: **UNKNOWN**;
- long-run WebVM reliability: **UNKNOWN / unqualified**;
- paid/live provider semantic success: **UNKNOWN** until retained exact-revision candidate→verifier→receipt evidence exists;
- capable-runner/every-host M4 qualification: **not established by hosted/prerequisite CI**;
- true blank-environment install: **not established by #193**.

## #200 onboarding hardening candidate

Open #200, exact candidate head `0c05074687afd50d1f2f53f93f7409e2e808af8e`, proposes persistent XDG venv/Station state, loopback-only default binding, opt-in convenience macro behavior, bounded corrupted-venv repair, bounded atomic shell-rc editing, and removal of premature browser-open side effects. It changes only `setup.sh` and its regression tests.

This is an **unaccepted candidate**, not current accepted behavior and not blank-environment evidence.

Observed exact-head candidate qualification now shows:

- Control Plane: **PASS**;
- Factory ownership: **PASS**;
- measured-evaluation binding: **PASS**;
- clean install: **PASS**;
- Controller/provider: **PASS**;
- Command Station: **PASS**;
- maintainer approval gate: **BLOCKED/FAIL** pending explicit exact-head maintainer attestation.

The earlier Controller/provider and Command Station failures belonged to the prior candidate head `c21ba57...` and remain historical evidence; they are not the status of the current #200 head. #200 is technically green in the observed automated scopes but remains unaccepted until the exact-head governance gate is satisfied.

## #202 / #203 development experiment evidence

These PRs are evidence-producing experiments, not implementation candidates to merge.

**#202 simple local-model PASS (historical experiment head).** On exact head `fee21d140c637300a534b9f498496e92b70d95da`, workflow run `35304614537` completed the real-model mission **PASS** with local Ollama/Qwen2.5-Coder 1.5B. Retained evidence records one integrated task, two provider calls, 846 reported tokens, 16.217 s wall clock, passing checks, model review approval, verification receipt and release export.

**#202 later heterogeneous DAG FAIL.** The same draft later advanced to `6b30125fd56bdbedcb1d6d04e6ee199dd697b315`. Run `35305663580` completed **FAIL** with retained DAG evidence: 1/3 tasks integrated, `STATS-002` remained repair-required after three attempts, `REPORT-003` stayed blocked by dependency, and run control escalated on `no_runnable_tasks`. Keep this FAIL alongside the earlier simple PASS; it prevents broadening the simple success into a DAG/recovery claim.

**#203 bounded M6 self-host FAIL.** On exact head `e123b90d012973bfd260ae5b955eebd4dbac48f0`, first authoritative run `35305550407` completed **FAIL**. Retained evidence records 0/1 integrated, three attempts, `max_iteration` escalation, 5526 reported tokens, no verification receipt and no release files. The final attempt was truncated before producing a verifiable candidate. This is negative research evidence, not autonomous recursive-improvement success.

None of these experiment outcomes establish paid/live Puter success, production reliability, current accepted self-hosting capability, or the preregistered R0–R5 systems hypothesis.

## Current build order

1. **If #200 is pursued, complete exact-head maintainer attestation before acceptance.** Its current exact head is technically green in the observed automated scopes; the earlier candidate-head technical failures remain historical evidence rather than current blockers.
2. **Retain exact-current-main Pages/deployment evidence separately if release policy requires it for `699e286...`.** No such exact-SHA run was observed in the current retained set; do not infer it from predecessor runs.
3. **Resolve the #133/#132 integration discrepancy.** Decide explicitly whether removal of #132 self-hosting/research-bundle tooling was intended retirement or an integration regression. Any restoration should be a focused reviewed implementation change, not a documentation rewrite.
4. **Continue #120/#126 WebVM reliability work from the #133 discriminators.** The shared CPython timeout/wait symptom is narrowed, but the exact ABI/emulation cause, relationship to older corruption and recurrence rate remain unknown.
5. **Refresh/requalify #190.** Its provider-channel recovery candidate requires current-tree reconciliation before integration; post-merge production retest remains separate if later accepted.
6. **Retest the live-provider semantic boundary on the exact deployed accepted revision.** Historical mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` remains `FAIL/BLOCKED`; paid/live success stays UNKNOWN until a candidate crosses protocol validation and normal verifier/receipt handling.
7. **Physically validate the accepted #186 fallback.** Do not broaden fallback success into a heavyweight-WebVM reliability claim.
8. **Execute true blank-environment installation and recovery/host-loss qualification for the exact release artifact.** #193 is a convenience path for a host that already has Python 3.11+.
9. **Complete the selected elapsed-soak tier.** Simulation is not elapsed wall-clock soak.
10. **Keep #139→ownership-baseline→fresh-qualification→#134 independent.** Unrelated merges do not clear that protected sequence.
11. **Refresh/requalify #152 and #177 before current release/research claims use them.**
12. **Use #202/#203 only as development evidence and keep their PASS/FAIL outcomes together.** Do not promote them into the frozen confirmatory R0–R5 result set.
13. **Freeze and run confirmatory research only after operational claims are bounded.**

## Planning and prototype work

- **#188** — accepted/on main as bounded AQ-GOV-001 adversarial apparatus.
- **#194** — accepted/on main as the completed-draft visibility/reopen repair.
- **#133** — accepted/on main as diagnostic tooling plus the current file-state change described above; diagnostic FAILs and UNKNOWN root cause remain visible.
- **#193** — accepted/on main as interactive setup convenience; not blank-environment release evidence.
- **#200** — open/unaccepted onboarding hardening candidate; current exact-head technical workflows PASS, maintainer-attestation remains **BLOCKED**.
- **#202** — draft experiment/evidence PR; simple local-model historical head PASS followed by a later heterogeneous DAG exact-head **FAIL**. Do not merge; retain both outcomes.
- **#203** — draft controlled M6 ImprovementSpec self-host experiment; first authoritative exact-head run **FAIL**, 0/1 integrated, evidence retained. Do not merge as capability.
- **#190** — open provider-channel recovery candidate; refresh/requalification required as applicable after current-main movement.
- **#152** — Qualification v1 framework candidate; refresh required before current release use.
- **#177** — IE-001 prototype candidate; reconcile/refresh before final qualification.
- **#160/#161/#162/#163/#164/#166/#167** — inference-engineering specifications/planning; no accepted production/performance/research claim merely from the specs.
- **#191** — closed unmerged; its automated PR-review workflow is not accepted governance.
- **#132** — historical self-hosting/research-bundle experiment; current implementation surface is absent after #133.

Planning artifacts, experiment-only branches and prototype-only candidates must not be counted as accepted production capability or used as a reason to change `implementation-status.yaml` by themselves.

## Release evidence rule

A merge onto main establishes that the merged bytes are part of the repository. It does not automatically establish every release, reliability, security or research claim associated with them.

Any claim touching ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, evidence schemas, physical-device reliability, live-provider success, recovery, soak, or the intent behind a removed accepted feature must remain scoped to retained evidence. Historical `FAIL`, `UNKNOWN` and `BLOCKED` results remain visible even when later revisions pass.