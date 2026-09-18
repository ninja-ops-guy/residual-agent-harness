# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@699e2869e294fe157b4bfd73a272057683a2f7e0`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`699e2869e294fe157b4bfd73a272057683a2f7e0`**, produced by merged **#193**. No later implementation PR has merged at this snapshot.

Material accepted state that remains current:

- **#188** — AQ-GOV-001 consensus-authority escalation lab is accepted adversarial test/research apparatus. It does not prove kernel/container/hypervisor/broker escape resistance.
- **#194** — Command Station retains the latest completed generated-spec job and exposes it as a clickable result that can repopulate Mission Intake.
- **#133** — WebVM guest-runtime discriminator tooling/workflows are accepted. Retained results narrow one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`. The exact lower-level CPython/i386 ABI/emulation cause remains **UNKNOWN**.
- **#193** — interactive native setup helper is accepted as operator convenience for hosts that already have Python 3.11+; it is not blank-environment qualification.

There is also a material integration/status caveat: #133 removed the accepted #132 protected self-hosting/research-bundle implementation, workflow, tests, example and dedicated research docs. #132 remains retained historical evidence, but its tooling is **not current accepted capability**. Whether the deletion represents intended retirement or an integration regression remains **UNKNOWN / unresolved**.

New development evidence since the prior status snapshot is mixed and deliberately retained as such:

- current #200 setup-hardening head is technically green in the observed automated scopes but still **BLOCKED** on exact-head maintainer attestation;
- #202 retained one simple real-local-model mission **PASS** on historical experiment head `fee21d...`, followed by a later heterogeneous DAG exact-head **FAIL** on `6b30125...`;
- #203 retained a first-authoritative M6 ImprovementSpec self-host experiment **FAIL** on `e123b90...`.

Paid/live Puter success, physical heavyweight-WebVM iPhone reliability, blank-environment install, host-loss/recovery evidence, selected elapsed soak, universal/capable-runner M4 qualification, and confirmatory R0–R5 research remain unestablished.

## Documentation regression: #192

PR #192 was titled as superseded but merged as `9de6d5820ef5e8735e6d6d9aef88c461085cd0de` immediately before #193. Its six documentation files were based on an earlier accepted-main snapshot and reintroduced stale current-state claims. That was a prose regression only; it did not supersede implementation or retained CI/evidence history.

This corrective docs branch restores the accepted state from exact current main and subsequent retained evidence without modifying runtime, ownership baselines, qualification anchors, protected Factory/M4 bytes, verifier authority, or evidence schemas.

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

The previous exact accepted `main@b3f00af29c7507f4c0e218884e491c2fc792d984` completed all seven ordinary first-attempt `push` workflows **PASS**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, Command Station and Pages/deployment. That evidence remains valid only for that exact predecessor revision and its named scopes.

On exact current `main@699e2869e294fe157b4bfd73a272057683a2f7e0`, the six observed applicable ordinary post-#193 `push` qualification workflows completed **PASS on attempt 1**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, and Command Station. No Pages/deployment run bound to this exact SHA was observed in the retained run set, so this is deliberately **not** described as a seven-workflow PASS.

Required claim discipline:

- #193 candidate-head named workflows: **PASS**;
- predecessor `main@b3f00af...` seven named workflows: **PASS** within their exact scopes;
- exact `main@699e286...` six observed applicable post-merge named workflows: **PASS** within their exact scopes;
- Pages/deployment on exact `main@699e286...`: **UNKNOWN / not observed in the retained exact-SHA run set**;
- universal/capable-runner M4 qualification: **not established**;
- blank-environment install: **not established by setup.sh or ordinary clean-install CI**;
- production long-run reliability: **not established**.

These exact-main PASS results do not broaden release, physical-device, provider, recovery, soak, or research claims.

## #200 setup-hardening candidate

Open PR #200, exact candidate head **`0c05074687afd50d1f2f53f93f7409e2e808af8e`**, proposes a focused hardening of the native setup path without changing Factory/M4, verifier, evidence, provider, or acceptance behavior.

The candidate proposes to:

- move default venv and Station state from `/tmp` to persistent XDG locations;
- change the default Station bind host from `0.0.0.0` to `127.0.0.1`;
- make the convenience shell macro opt-in, including non-TTY/piped execution;
- repair a broken existing venv with bounded `venv --clear` behavior;
- constrain shell startup-file edits to marked blocks with atomic same-directory replacement;
- recognize exact #193 legacy snippets while refusing to overwrite unrelated user-defined `residual` functions;
- stop opening a browser before a server has actually been started;
- invoke installation through the venv interpreter explicitly.

This is **unaccepted candidate behavior**, not current-main behavior. It remains onboarding hardening rather than blank-environment qualification or a portability proof.

Observed exact-head #200 workflow status now:

- Control Plane: **PASS**;
- Factory ownership: **PASS**;
- measured-evaluation binding: **PASS**;
- clean install: **PASS**;
- Controller/provider: **PASS**;
- Command Station: **PASS**;
- maintainer approval gate: **BLOCKED/FAIL** pending explicit exact-head maintainer attestation.

The earlier Controller/provider and Command Station failures belonged to prior head `c21ba57...` and remain historical evidence; they are not the status of current head `0c05074...`. #200 is technically green in the observed automated scopes, but it is **not accepted** until exact-head governance is satisfied.

## #202 retained real-model experiment evidence

Draft PR #202 is explicitly an experiment/evidence PR and must not be treated as merge-ready product capability.

### Simple mission: bounded PASS on historical experiment head

On exact experiment head **`fee21d140c637300a534b9f498496e92b70d95da`**, workflow run **`35304614537`** completed the dedicated `real-model-mission` job **PASS** on attempt 1. A fresh GitHub Actions runner installed Ollama and used `qwen2.5-coder:1.5b` locally from only a behavioral specification for `calculator.py:add(a,b)`.

The retained `real-model-mission-evidence` artifact records:

- run outcome: **SUCCESS**;
- integrated: **1/1**;
- passes: **1**;
- provider calls: **2** total, runner + reviewer;
- reported tokens: **846**;
- wall clock: **16.217 s**;
- compile check: **PASS**;
- behavioral command check: **PASS**;
- reviewer approval: **PASS**;
- verification receipt: present;
- release export: present.

This establishes one bounded real-local-model candidate→checks→review→integration→receipt/export path on that exact experiment revision. It does **not** establish paid/live Puter success, model quality generally, production reliability, heterogeneous DAG reliability, or the central R0–R5 hypothesis.

### Later heterogeneous DAG: retained FAIL

PR #202 later advanced to exact head **`6b30125fd56bdbedcb1d6d04e6ee199dd697b315`**. Workflow run **`35305663580`** completed **FAIL** and retained `dag-real-model-mission-evidence`.

The retained evidence records:

- batch outcome: **escalated**;
- integrated: **1/3**;
- `CORE-001`: checks/review/integration **PASS** with a verification receipt;
- `STATS-002`: a deterministic injected syntax fault triggered repair; later attempts compiled but failed the behavioral check with `NameError: name 'math_core' is not defined` and remained `repair_required` after three attempts;
- `REPORT-003`: remained ready and did not run because its dependency did not integrate;
- run-control brake: `dispatch`, reason `no_runnable_tasks`;
- reported tokens: **3174**;
- wall clock: **78.675 s**.

This FAIL is retained evidence, not CI noise to rerun away. It prevents broadening the earlier simple success into a general DAG/recovery claim.

## #203 M6 ImprovementSpec self-host experiment

Draft PR #203 is a controlled research experiment against frozen baseline `main@699e286...`. It does not modify main, protected M4, verifier authority, evidence schemas, or promotion controls; generated implementation remains isolated inside the mission/export boundary.

On exact head **`e123b90d012973bfd260ae5b955eebd4dbac48f0`**, first authoritative run **`35305550407`** completed **FAIL** and retained `m6-improvementspec-research-evidence`.

The retained evidence records:

- batch outcome: **escalated**;
- integrated: **0/1**;
- attempts: **3**;
- first attempt: import/behavior check failed because `ImprovementSpec` was absent;
- second attempt: compile and behavior checks failed with an unclosed parenthesis;
- third attempt: model output was truncated before a verifiable candidate was produced;
- run-control brake: `max_iteration` after three passes;
- reported tokens: **5526**;
- wall clock: **125.374 s**;
- verification receipt: **absent**;
- release files: **none**.

This is useful negative research evidence. It does **not** establish autonomous recursive self-improvement and does not restore #132 as current accepted self-maintenance capability.

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

Multiple #133 discriminator workflows intentionally completed **FAIL** because they reproduced the defect under study. Those FAIL outcomes remain diagnostic evidence and are not qualification passes.

## #133 / #132 integration discrepancy

Merged #132 had previously accepted bounded protected self-hosting/research-bundle tooling, including `residual/self_maintenance.py`, `residual/research_bundle.py`, supporting scripts/tests, a protected-self-hosting workflow, an example mission and dedicated research documentation.

The final #133 merge removed that surface. Current-state interpretation is byte-accurate:

- #132 historical retained experiment/evidence: **still historical evidence**;
- #132 self-maintenance/research-bundle implementation on current main: **ABSENT / not current capability**;
- reason the accepted feature was removed: **not established by retained evidence**;
- intended retirement vs accidental integration regression: **UNKNOWN / unresolved**;
- restoration: **must be a separate focused reviewed implementation change if desired**, not silently reconstructed in documentation.

Draft #203 adds experiment apparatus only and its generated candidate did not integrate; it does not change this current-capability boundary.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of those historical invalid responses: **UNKNOWN**.

Merged #179 changed the bounded build-output path. Merged #183 repaired provider-session lifecycle behavior. Merged #189 repaired the provider-helper COI/CORP publication boundary. None alone establishes successful live inference.

The #202 local-Ollama success is not Puter evidence; it used a different provider and environment. A fresh retained real-account mission on the exact deployed accepted revision is still required before paid/live provider success can become PASS. It must cross provider protocol validation and proceed through normal candidate/verifier/receipt handling.

## iPhone/WebKit and WebVM reliability boundary

The accepted #186 fallback detects iPhone/iPad/iPod and iPadOS WebKit before heavyweight guest/disk boot and routes that profile to the lightweight walkthrough, retaining the full VM only as an explicit diagnostic override.

This is a fallback contract, not proof that heavyweight WebVM is reliable on physical iPhone Safari. Published physical-device validation remains open, and the lower-level WebKit process-kill cause remains **UNKNOWN**.

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
- **#200** — open/unaccepted setup-hardening candidate. Current exact-head technical workflows PASS; maintainer attestation remains **BLOCKED/FAIL**.
- **#201** — open draft frontend/onboarding candidate. It remains unaccepted and requires its own Pages/live-provider UX evidence before any current-capability claim changes.
- **#202** — draft experiment/evidence PR. Retain the historical simple local-model **PASS** and later heterogeneous DAG exact-head **FAIL** together; do not merge as product capability.
- **#203** — draft controlled M6 self-host experiment. First authoritative exact-head run **FAIL**, 0/1 integrated, evidence retained; do not describe as autonomous self-improvement success.
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

- the six observed exact-current-main PASS workflows establish an unobserved exact-SHA Pages/deployment result or broader release readiness;
- current ordinary workflow PASS establishes every-host/capable-runner M4 qualification or broader production readiness;
- setup.sh establishes true blank-environment release qualification;
- #200's proposed safer defaults are current accepted behavior before merge;
- #202's simple local-model PASS establishes heterogeneous DAG reliability, paid/live Puter success, production reliability, or the central research hypothesis;
- the later #202 DAG FAIL may be discarded because an earlier simpler experiment passed;
- #203 establishes autonomous recursive self-improvement;
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

1. If #200 is pursued, obtain exact-head maintainer attestation before merge. Its current observed technical workflows are green; earlier candidate-head technical failures remain historical evidence.
2. If release policy requires Pages/deployment evidence on exact `main@699e286...`, retain that exact-SHA run separately; none was observed in the current exact-SHA run set.
3. Keep #202/#203 as development evidence and retain both positive and negative outcomes; do not promote them into frozen confirmatory R0–R5 results.
4. Make an explicit disposition for the #133 removal of #132 self-hosting/research-bundle tooling: intentional retirement vs focused restoration/reintroduction.
5. Continue #120/#126 from the #133 discriminators until a lower-level cause or predefined reliability campaign justifies a stronger operational claim.
6. Refresh/requalify #190, #152 and #177 as applicable after material main movement.
7. Retain a fresh real-account Puter candidate→verifier→receipt success before claiming live-provider PASS.
8. Validate the accepted #186 fallback on a physical device without turning fallback success into a heavyweight-WebVM claim.
9. Execute true blank-environment install and recovery/host-loss qualification for the exact release artifact.
10. Complete the selected elapsed-soak tier with retained first-failure evidence.
11. Preserve the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence.
12. Freeze and run confirmatory R0–R5/degradation/heterogeneous-routing studies only under the stated research protocol.

## Documentation authority

Use this order when determining current truth:

1. exact code at the revision being discussed;
2. exact-head workflow output and retained machine-readable artifacts;
3. open qualification/security/reliability issues and explicit release policy;
4. submitted maintainer/protected-byte/ownership-baseline review records;
5. this current-status document;
6. `implementation-status.yaml` for implementation traceability;
7. historical specs/snapshots/experiments for design intent and historical evidence, not current qualification claims.