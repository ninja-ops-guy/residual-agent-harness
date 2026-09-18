# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@699e2869e294fe157b4bfd73a272057683a2f7e0`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`699e2869e294fe157b4bfd73a272057683a2f7e0`**, produced by merged **#193**. Immediately before it, **#192** merged an older documentation refresh whose source state predated later accepted changes; that made several current-state documents materially stale again. This corrective docs branch restores the actual accepted state rather than treating the #192 prose as implementation authority.

Material accepted changes that must remain visible:

- **#188** — AQ-GOV-001 consensus-authority escalation lab. It assumes ten of ten workers approve privilege escalation and exercises existing quarantine/WorkerContract/AttemptGuard boundaries. It is accepted adversarial test/research apparatus, not proof of kernel/container/hypervisor/broker escape resistance.
- **#194** — Command Station retains the latest completed generated-spec job and exposes it as a clickable result that can repopulate Mission Intake after the original in-memory watcher is gone.
- **#133** — WebVM guest-runtime discriminator tooling/workflows. Retained results narrow one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`. Direct libc waits continue beyond the same narrow boundary. The exact CPython/i386 ABI/emulation mechanism and relationship to the older corruption family remain **UNKNOWN**.
- **#193** — interactive native setup helper. `setup.sh` detects Python 3.11+, creates/reuses a dedicated venv, installs the checkout, exports its `bin` directory to the selected shell startup file, optionally installs a no-argument `residual` serve macro, and prints/attempts to open the local Station URL.

There is also a material integration/status caveat: #133 removed the accepted #132 protected self-hosting/research-bundle implementation, workflow, tests, example and dedicated research docs. Earlier review records explicitly called those deletions an integration blocker for a supposedly diagnostic-only PR. Therefore #132 remains retained historical evidence, but its tooling is **not current accepted capability**. Whether the deletion represents intended retirement or an integration regression remains **UNKNOWN / unresolved**.

Paid/live Puter success, physical heavyweight-WebVM iPhone reliability, blank-environment install, host-loss/recovery evidence, selected elapsed soak, universal/capable-runner M4 qualification, and confirmatory R0–R5 research remain unestablished.

## Documentation regression: #192

PR #192 was titled as superseded, but it nevertheless merged as `9de6d5820ef5e8735e6d6d9aef88c461085cd0de` immediately before #193. Its six documentation files were based on the earlier `main@dcf1e507...` state and consequently reintroduced stale claims such as treating #188/#194/#193 as unaccepted candidates and omitting the accepted #133/#132 file-state discrepancy.

Interpretation:

- #192 merge status: **PASS / merged as repository bytes**;
- accuracy of its current-state claims after the later accepted changes it omitted: **STALE**, not authority over implementation history;
- corrective action: documentation-only restoration from exact current main;
- runtime/trust-boundary implication: **none** — #192 changed documentation only.

Historical implementation and CI evidence is not erased by a later stale prose merge.

## Accepted #193 interactive setup path

PR #193 final candidate head was `d97104958a235d9439fd3c36cc72221ba454b3cc`; it merged as current main `699e2869e294fe157b4bfd73a272057683a2f7e0`.

The accepted `setup.sh` convenience path:

- selects an available Python 3.11+ interpreter;
- creates/reuses `${RESIDUAL_VENV:-/tmp/residual-venv}`;
- installs this checkout editable into that venv;
- adds the venv `bin` directory to `.bashrc`, `.zshrc`, or `.profile` as applicable;
- optionally installs a shell `residual()` wrapper so `residual` with no arguments serves Command Station while arguments pass through to the real CLI;
- stores the macro toggle in `${RESIDUAL_SETTINGS:-$HOME/.residual-settings}`;
- defaults the serve host/port/data directory to `0.0.0.0:8765` and `/tmp/residual-station-data`, with environment-variable overrides;
- attempts to open the local URL and otherwise prints it.

This is operator convenience, not a true bare/blank-environment qualification result. A host Python 3.11+ installation and normal OS/network prerequisites remain external assumptions. Because the optional macro defaults to `0.0.0.0`, operators who require loopback-only binding should use `RESIDUAL_HOST=127.0.0.1` or invoke `residual serve` explicitly with a loopback host.

The observed exact-head PR workflows on `d971049...` completed **PASS** for Control Plane, Factory ownership, clean install, Controller/provider, measured-evaluation binding, Command Station and the maintainer approval gate before merge.

## Exact-current-main qualification

The previous exact accepted `main@b3f00af29c7507f4c0e218884e491c2fc792d984` completed all seven ordinary first-attempt `push` workflows **PASS**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, Command Station and Pages/deployment.

That evidence remains valid for `b3f00af...`; it is not automatically inherited by `699e286...`.

At this status check, the post-merge workflow set on exact `main@699e286...` had started and applicable runs were still being observed. Until the exact merged revision's applicable workflows complete, post-merge qualification is **PENDING**. Candidate-head PASS and predecessor-main PASS must not be relabeled as merged-sha PASS.

Required claim discipline:

- #193 candidate-head named workflows: **PASS**;
- predecessor `main@b3f00af...` seven named workflows: **PASS**;
- exact `main@699e286...` post-merge workflow set: **PENDING** at this snapshot;
- universal/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established by setup.sh or ordinary clean-install CI**;
- production long-run reliability: **not established**.

## #133 WebVM runtime diagnostics

Retained diagnostic evidence supports the following narrow classification:

- positive-duration `time.sleep()` fails under the tested WebVM guest around a narrow process-local call boundary;
- empty `select.select([], [], [], timeout)` reproduces the same `_PyTime_t` overflow family;
- zero-duration sleep and tested monotonic clock-read paths pass beyond that boundary;
- native i386 controls pass;
- direct libc `nanosleep` / `clock_nanosleep` controls continue beyond the same boundary;
- fresh guest CPython process creation resets or avoids the process-local boundary in paired tests;
- Mission Control, its persistent worker, background scheduling and a second interpreter are not necessary preconditions for the reproduced symptom.

The strongest supported description is a **WebVM-specific CPython positive-duration timeout/wait conversion-path failure** affecting at least `time.sleep()` and empty `select.select()` in the tested guest/runtime combination.

Required non-claims:

- exact CPython/i386 ABI, emulation, handle/resource, syscall or conversion defect: **UNKNOWN**;
- time64/`ENOSYS` correlation as causal proof: **UNKNOWN / not established**;
- relationship to historical `_sha512`, impossible-constructor, allocator or poisoned-guest evidence: **UNKNOWN**;
- long-run WebVM reliability: **not established**;
- production fix: **not established by diagnostic instrumentation**.

Multiple #133 discriminator workflows intentionally completed **FAIL** because they reproduced the defect under study. Those FAIL outcomes remain diagnostic evidence and are not CI noise to rerun away.

## #133 / #132 integration discrepancy

Merged #132 had previously accepted bounded protected self-hosting/research-bundle tooling, including `residual/self_maintenance.py`, `residual/research_bundle.py`, supporting scripts/tests, a protected-self-hosting workflow, an example mission and dedicated research documentation.

The final #133 merge removed that surface. Current-state interpretation is byte-accurate:

- #132 historical retained experiment/evidence: **still historical evidence**;
- #132 self-maintenance/research-bundle implementation on current main: **ABSENT / not current capability**;
- reason the accepted feature was removed: **not established by retained evidence**;
- intended retirement vs accidental integration regression: **UNKNOWN / unresolved**;
- restoration: **must be a separate focused reviewed implementation change if desired**, not silently reconstructed in documentation.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of those historical invalid responses: **UNKNOWN**.

Merged #179 changed the bounded build-output path. Merged #183 repaired provider-session lifecycle behavior. Merged #189 repaired the provider-helper COI/CORP publication boundary. None alone establishes successful live inference.

A fresh retained real-account mission on the exact deployed accepted revision is required before paid/live provider success can become PASS. It must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling.

## iPhone/WebKit boundary

The accepted #186 fallback detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot and routes that profile to the lightweight walkthrough, retaining the full VM only as an explicit diagnostic override.

This is a fallback contract, not proof that heavyweight WebVM is reliable on physical iPhone Safari. Published physical-device validation remains open, and the lower-level WebKit process-kill cause remains **UNKNOWN**.

## WebVM reliability boundary

Issues #120 and #126 remain open. #133 substantially narrows one runtime symptom and adds retained discriminators, but it does not prove that the broader poisoned-guest/interpreter/allocator corruption family shares the same cause, does not quantify an acceptable recurrence rate, and does not establish a production fix.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

Accepted #185 and #187 protected-byte/ownership-baseline changes remain scoped to their reviewed behavior. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent and must not be treated as cleared by unrelated green CI.

This documentation branch changes no Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier/evidence schemas, provider authorization or acceptance authority.

## Research and planning state

- **#188** — accepted/on main as bounded AQ-GOV-001 adversarial apparatus. It is not a universal security proof.
- **#133** — accepted/on main as diagnostic tooling plus the current file-state change described above. Its diagnostic FAIL results remain retained evidence and its root cause remains UNKNOWN.
- **#194** — accepted/on main as the completed-draft UI/state repair.
- **#193** — accepted/on main as interactive native setup convenience; it is not blank-environment release evidence.
- **#190** — provider-channel recovery candidate remains open/unaccepted and requires refresh/requalification after material main movement.
- **#152** — Qualification v1 framework candidate; older results must be refreshed before current release claims use them.
- **#177** — IE-001 prototype candidate; previous evidence remains candidate-head evidence and needs reconciliation/requalification before final IE-001 claims.
- **#191** — closed unmerged; its automated PR Agent workflow is not accepted governance.
- **#132** — historical merged self-hosting/research-bundle experiment; its implementation surface is absent from current main after #133.

Merged #168 continues to define normal repository merge control as:

`automated qualification/review appropriate to scope → exact-head maintainer attestation → merge`

This is maintainer-reviewed with automated qualification, not independent human assurance.

## Release and research non-claims

The project does **not** yet claim that:

- candidate-head or predecessor-main PASS can substitute for exact `main@699e286...` post-merge evidence;
- current ordinary workflow PASS establishes every-host/capable-runner M4 qualification or broader production readiness;
- setup.sh establishes true blank-environment release qualification;
- intentional #133 diagnostic FAILs are ordinary qualification PASSes;
- #133 establishes the exact lower-level WebVM/CPython root cause or long-run reliability;
- #132 self-maintenance/research-bundle tooling remains current capability after its files were removed;
- successful paid/live Puter inference has been retained on exact current main;
- #186 proves heavyweight WebVM reliability on physical iPhone Safari;
- blank-environment install/recovery qualification is complete;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- #190/#152/#177 are accepted current-main capability;
- the solo-maintainer model supplies independent human assurance;
- confirmatory live-model evaluation has established the central reliability hypothesis.

## Next gates

1. Complete and retain the exact-current-main post-#193 workflow/deployment set; preserve any first failure rather than replacing it with a rerun-only success story.
2. Make an explicit disposition for the #133 removal of #132 self-hosting/research-bundle tooling: intentional retirement vs focused restoration/reintroduction.
3. Continue #120/#126 from the #133 discriminators until a lower-level cause or predefined reliability campaign justifies a stronger operational claim.
4. Refresh/requalify #190, #152 and #177 as applicable after material main movement.
5. Retain a fresh real-account Puter candidate→verifier→receipt success before claiming live-provider PASS.
6. Validate the accepted #186 fallback on a physical device without turning fallback success into a heavyweight-WebVM claim.
7. Execute true blank-environment install and recovery/host-loss qualification for the exact release artifact.
8. Complete the selected elapsed-soak tier with retained first-failure evidence.
9. Preserve the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence.
10. Freeze and run confirmatory R0–R5/degradation/heterogeneous-routing studies only under the stated research protocol.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head workflow output and retained machine-readable artifacts;
3. open qualification/security/reliability issues and explicit release policy;
4. submitted maintainer/protected-byte/ownership-baseline review records;
5. this current-status document;
6. `implementation-status.yaml` for implementation traceability;
7. historical specs/snapshots/experiments for design intent and historical evidence, not current qualification claims.
