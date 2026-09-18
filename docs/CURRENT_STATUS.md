# RESIDUAL current status

_Current-state check: 2026-09-17 UTC against `main@b3f00af29c7507f4c0e218884e491c2fc792d984`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` advanced from the previously documented `dcf1e507...` through three material accepted merges:

- **#188** — AQ-GOV-001 consensus-authority escalation lab. It assumes ten of ten workers approve privilege escalation and exercises existing quarantine/WorkerContract/AttemptGuard boundaries. It is accepted adversarial test/research apparatus, not proof of kernel/container/hypervisor/broker escape resistance.
- **#194** — Command Station retains the latest completed generated-spec job and exposes it as a clickable result that can repopulate Mission Intake after the original in-memory watcher is gone.
- **#133** — WebVM guest-runtime discriminator tooling/workflows. Retained results narrow one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`. Direct libc waits continue beyond the same narrow boundary. The exact CPython/i386 ABI/emulation mechanism and relationship to the older corruption family remain **UNKNOWN**.

There is also a material integration/status caveat: #133 removed the accepted #132 protected self-hosting/research-bundle implementation, workflow, tests, example, and dedicated research docs. Earlier review records explicitly called those deletions an integration blocker for a supposedly diagnostic-only PR. The deletion nevertheless landed on main. Therefore #132 remains retained historical evidence, but its tooling is **not current accepted capability**. Whether the deletion represents intended retirement or an integration regression is unresolved and should be handled explicitly rather than inferred from the merge.

All seven ordinary first-attempt `push` workflows on exact current main completed **PASS**, including Pages/deployment on attempt 1.

Paid/live Puter success, physical heavyweight-WebVM iPhone reliability, blank-environment install, host-loss/recovery evidence, selected elapsed soak, universal/capable-runner M4 qualification, and confirmatory R0–R5 research remain unestablished.

## Accepted merges since `dcf1e507...`

### #188 — AQ-GOV-001

PR #188 final head was `10ec36065ece133cb48ec38d595dee3e1cf9d83e`; it merged as `07b8559a5a7639d3f8fac27be4977bcf567d90e3`.

The accepted lab tests one narrow invariant: unanimous worker consensus is not authorization to enlarge worker authority. The scenario requires malicious proposals to be denied through `QuarantineStore`, independently violate the issued immutable `WorkerContract` through `AttemptGuard`, invoke the stop hook, and never reach a malicious executor. A harmless positive control must remain usable and end in `CANDIDATE`, not `ACCEPTED`.

Claim boundary:

- accepted repository capability: **PASS / on main** for the lab implementation;
- authority-escalation claim: bounded to the tested software path and attack classes;
- kernel/container/hypervisor/broker escape resistance: **UNKNOWN / not established by AQ-GOV-001**;
- universal autonomous-agent safety: **not claimed**.

### #194 — completed draft visibility/reopen

PR #194 final head was `ce987cd876bc826695dab8a8a2487b1bb9141d76`; it merged as `3e3d8055b255c1dd99149c7638f42d1e38ec69c7`.

The accepted change keeps the latest completed `draft-spec` result visible in the operation tray, makes that completed job clickable, and reloads the generated Markdown into Mission Intake for review and mission creation. Browser regression coverage exercises reopening a persisted completed draft after the original watcher is gone.

This is a UI/state-presentation repair. It does not broaden Factory/M4 authority, verifier semantics, provider budgets, or evidence schemas.

### #133 — WebVM runtime diagnostics

PR #133 final head was `be324a927c938829a7dcfd811d4fd37a35b8152a`; it merged as current main `b3f00af29c7507f4c0e218884e491c2fc792d984`.

Retained diagnostic evidence supports the following narrow classification:

- positive-duration `time.sleep()` fails under the tested WebVM guest around a narrow process-local call boundary;
- empty `select.select([], [], [], timeout)` reproduces the same `_PyTime_t` overflow family;
- zero-duration sleep and tested monotonic clock-read paths pass beyond that boundary;
- native i386 controls pass;
- direct libc `nanosleep` / `clock_nanosleep` controls continue beyond the same boundary;
- fresh guest CPython process creation resets or avoids the process-local boundary in the paired tests;
- Mission Control, its persistent worker, background scheduling, and a second interpreter are not necessary preconditions for the reproduced symptom.

The strongest supported description is a **WebVM-specific CPython positive-duration timeout/wait conversion-path failure** affecting at least `time.sleep()` and empty `select.select()` in the tested guest/runtime combination.

Required non-claims:

- exact CPython/i386 ABI, emulation, handle/resource, syscall, or conversion defect: **UNKNOWN**;
- time64/`ENOSYS` correlation as causal proof: **UNKNOWN / not established**;
- relationship to historical `_sha512`, impossible-constructor, allocator, or poisoned-guest evidence: **UNKNOWN**;
- long-run WebVM reliability: **not established**;
- production fix: **not established by diagnostic instrumentation**.

On the exact #133 final candidate head, ordinary Factory ownership, measured-evaluation binding, Browser VM Demo, Control Plane, clean install, Controller/provider, Command Station, Pages, and the maintainer approval gate completed **PASS**. Multiple WebVM discriminator workflows intentionally completed **FAIL** because they reproduced the defect under test. Those FAIL outcomes are retained diagnostic evidence, not CI noise to rerun away.

## #133 / #132 integration discrepancy

Merged #132 had previously accepted bounded protected self-hosting/research-bundle tooling, including `residual/self_maintenance.py`, `residual/research_bundle.py`, supporting scripts/tests, a protected-self-hosting workflow, an example mission, and dedicated research documentation.

During #133 review, the branch was explicitly flagged as non-mergeable-as-constructed because it deleted those accepted #132 files despite describing itself as diagnostic-only. A later autonomous review also called the deletion material scope creep and recommended either explicitly declaring retirement or splitting it into a separate change.

The final #133 merge still removed that surface. Current-state interpretation must therefore be byte-accurate:

- #132 historical retained experiment/evidence: **still historical evidence**;
- #132 self-maintenance/research-bundle implementation on current main: **ABSENT / not current capability**;
- reason the accepted feature was removed: **not established by retained evidence**;
- intended retirement vs accidental integration regression: **UNKNOWN / unresolved**;
- restoration: **must be a separate focused reviewed change if desired**, not silently reconstructed in documentation.

This documentation update does not restore, rewrite, or alter any of those implementation bytes.

## Exact-current-main qualification

All seven ordinary first-attempt `push` workflows on exact `main@b3f00af...` are **PASS**:

| Workflow | Exact-current-main outcome |
| --- | --- |
| Factory ownership gate | **PASS** — run `35288585067` |
| M4 qualification runner prerequisites | **PASS** — run `35288584989` |
| Measured evaluation acceptance binding | **PASS** — run `35288585010` |
| Clean install qualification | **PASS** — run `35288585050` |
| Controller and provider contracts | **PASS** — run `35288584962` |
| Command Station checks | **PASS** — run `35288585136` |
| Deploy GitHub Pages | **PASS** — run `35288585007`, attempt 1 |

Claim discipline at this snapshot:

- accepted bytes on main: **PASS / merged**;
- seven named current-main ordinary workflows above: **PASS within their exact scopes**;
- #133 exact-candidate ordinary technical workflows: **PASS within their named scopes**;
- #133 discriminator FAILs: **retained FAIL evidence by design**;
- universal/capable-runner M4 qualification: **not established**;
- production WebVM long-run reliability: **not established**.

Historical exact-main results remain bound to their named revisions. The first post-#189 `main@dcf1e507...` seven-workflow set also completed PASS on attempt 1, but the current statement is based on fresh exact-current-main results rather than inherited qualification.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of those historical invalid responses: **UNKNOWN**.

Merged #179 changed the bounded build-output path. Merged #183 repaired provider-session lifecycle behavior. Merged #189 repaired the provider-helper COI/CORP publication boundary. None alone establishes successful live inference.

A fresh retained real-account mission on the exact deployed accepted revision is required before paid/live provider success can become PASS. It must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling.

## Provider-session candidate #190

PR #190 remains **open and unmerged**. Its current head is `2e4fda99bb6a21e37cabc7fd9b6b2eb185b66623`; its recorded base predates #133 current main. Earlier candidate qualification is therefore historical to that candidate head after the material main move.

The candidate changes browser provider-channel session recovery only. It does not claim live Puter success, physical-iPhone reliability, blank-environment qualification, elapsed soak, or production reliability. Before integration it should be refreshed/reconciled against current main and freshly qualified under applicable governance. Any accepted merge still requires production provider-session recovery retest.

## iPhone/WebKit boundary

The accepted #186 fallback detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot and routes that profile to the lightweight walkthrough, retaining the full VM only as an explicit diagnostic override.

This is a fallback contract, not proof that heavyweight WebVM is reliable on physical iPhone Safari. Published physical-device validation remains open, and the lower-level WebKit process-kill cause remains **UNKNOWN**.

## WebVM reliability boundary

Issues #120 and #126 remain open. #133 substantially narrows one runtime symptom and adds retained discriminators, but it does not prove that the broader poisoned-guest/interpreter/allocator corruption family shares the same cause, does not quantify an acceptable recurrence rate, and does not establish a production fix.

Merged recovery/diagnostic/provider changes remain bounded mitigations and observability improvements. They do not, individually or collectively, justify a blanket long-run reliability PASS without a predefined repeated-run campaign and retained first-failure evidence.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

Accepted #185 and #187 protected-byte/ownership-baseline changes remain scoped to their reviewed behavior. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent and must not be treated as cleared by unrelated green CI.

This documentation branch changes no Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier/evidence schemas, provider authorization, or acceptance authority.

## Research and planning state

- **#188** — now **accepted/on main** as bounded AQ-GOV-001 adversarial apparatus. It is not a universal security proof.
- **#133** — now **accepted/on main** as diagnostic tooling plus the current file-state change described above. Its diagnostic FAIL results remain retained evidence and its root cause remains UNKNOWN.
- **#194** — now **accepted/on main** as the completed-draft UI/state repair.
- **#193** — interactive setup-script candidate remains open/unaccepted and predates current main; do not count it as current operator behavior until refreshed/qualified/merged.
- **#190** — provider-channel recovery candidate remains open/unaccepted; refresh/requalification is required after the main move.
- **#152** — Qualification v1 framework candidate; older results must be refreshed before current release claims use them.
- **#177** — IE-001 prototype candidate; previous evidence remains candidate-head evidence and needs reconciliation/requalification before final IE-001 claims.
- **#191** — closed unmerged; its automated PR Agent workflow is not accepted governance.
- **#132** — historical merged self-hosting/research-bundle experiment; its implementation surface is absent from current main after #133 and must not be described as current capability.

Merged #168 continues to define normal repository merge control as:

`automated qualification/review appropriate to scope → exact-head maintainer attestation → merge`

This is maintainer-reviewed with automated qualification, not independent human assurance.

## Release and research non-claims

The project does **not** yet claim that:

- current-main ordinary workflow PASS establishes every-host/capable-runner M4 qualification or broader production readiness;
- intentional #133 diagnostic FAILs are ordinary qualification PASSes;
- #133 establishes the exact lower-level WebVM/CPython root cause;
- #133 proves long-run WebVM reliability or a production fix;
- #132 self-maintenance/research-bundle tooling remains current capability after its files were removed;
- the reason for #132's removal is known from retained evidence;
- successful paid/live Puter inference has been retained on exact current main;
- #186 proves heavyweight WebVM reliability on physical iPhone Safari;
- blank-environment install/recovery qualification is complete;
- simulated soak is equivalent to elapsed 24h/72h/30d operation;
- #190/#193/#152/#177 are accepted current-main capability;
- the solo-maintainer model supplies independent human assurance;
- confirmatory live-model evaluation has established the central reliability hypothesis.

## Next gates

1. Make an explicit disposition for the #133 removal of #132 self-hosting/research-bundle tooling: intentional retirement vs focused restoration/reintroduction. Do not let docs silently decide that implementation question.
2. Continue #120/#126 from the #133 discriminators until a lower-level cause or predefined reliability campaign justifies a stronger operational claim.
3. Refresh/requalify #190, #193, #152, and #177 as applicable after the material main move.
4. Retain a fresh real-account Puter candidate→verifier→receipt success before claiming live-provider PASS.
5. Validate the accepted #186 fallback on a physical device without turning fallback success into a heavyweight-WebVM claim.
6. Execute true blank-environment install and recovery/host-loss qualification for the exact release artifact.
7. Complete the selected elapsed-soak tier with retained first-failure evidence.
8. Preserve the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence.
9. Freeze and run confirmatory R0–R5/degradation/heterogeneous-routing studies only under the stated research protocol.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head workflow output and retained machine-readable artifacts;
3. open qualification/security/reliability issues and explicit release policy;
4. submitted maintainer/protected-byte/ownership-baseline review records;
5. this current-status document;
6. `implementation-status.yaml` for implementation traceability;
7. historical specs/snapshots/experiments for design intent and historical evidence, not current qualification claims.
