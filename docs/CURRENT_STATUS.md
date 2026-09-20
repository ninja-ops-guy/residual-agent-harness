# RESIDUAL current status

_Current-state check: 2026-09-20 UTC against `main@2f9dda3882f39c28a1c766859b1bf9579eea7911`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`2f9dda3882f39c28a1c766859b1bf9579eea7911`**, produced by merged **#338** on 2026-09-19 after merged **#336** and **#337**.

The newly accepted protected change is deliberately scoped:

- **#338** adds bounded contention-only admission retry to the idempotent `RuntimeJournal.__init__` schema/metadata write phase and advances the protected Factory ownership pin for `residual/factory/runtime_journal.py` to the reviewed blob `8f691b2a68d01d1df08ef7c79f8281805775b680`.
- non-contention errors and deadline exhaustion remain fail-closed;
- current-main Factory ownership CI is **PASS**;
- the merge does **not** establish blanket Factory/M4, sandbox, verifier, evidence-schema, provider, release or every-host qualification.

The #338 exact PR head had a matching maintainer attestation. Its PR-Agent advisory was nevertheless **FAIL / unavailable** because both configured OpenAI review models returned `credit_balance_exhausted`; no substantive advisory was published. That missing advisory remains an evidence/governance gap and is not retroactively a PASS.

Earlier accepted #307, #260, #288, #320, #328, #330, #337, and #336 retain their previously reviewed scope.

Separate from the exact-current-main Pages result, open owner issue **#353** now records an **AUD-1 P0 pre-release convergence gate** against frozen `main@2f9dda38...`. The owner disposition marks F1-F3 as P0 BLOCKER findings and keeps F4/F6 in the same P0 remediation lane. No exact remediation head exists yet. Release convergence is therefore **BLOCKED by the declared P0 security gate**, while the repair status of any future candidate remains **UNKNOWN** until the required adversarial regressions, physical reconnect cases, independent Mason re-audit, exact-head qualification, and owner attestation exist.

## Exact-current-main production qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For exact current main `2f9dda38...`:

- production Pages run **`35452581203`**, attempt 1: **PASS**;
- generated desktop+narrow artifact/browser proof: **PASS**;
- Pages deployment: **PASS**;
- published desktop exact-revision and real-guest execution: **PASS**;
- published narrow-Chromium verification: **PASS**;
- retained live-proof artifact: **`webvm-live-proof-35452581203-1`**;
- artifact SHA-256: **`eed4f0722e43af9362eb62bad122de3521e6f391d92b6388b582c92ef1bff63f`**;
- rerun used: **no**.

This closes the publication/browser/real-guest production Pages gate for this exact revision only. It does **not** establish blank-environment install, host-loss/recovery, selected elapsed soak, paid/live provider semantic success, model quality, physical heavyweight-WebVM iPhone reliability, every-host M4 qualification, or independent review.

Predecessor evidence remains revision-bound and must not be rewritten:

- `d89c5d94...` run `35449637725`, attempt 1: **FAIL** at the narrow retained-evidence path; lower-level cause remains **UNKNOWN** because the failing assertion compounded artifact-existence and `verify_run(...)` predicates;
- `3bfa6aba...`: retained production Pages **FAIL**;
- `e7b72ad...`: retained production Pages **FAIL**;
- `0a675017...` run `35431634267`, attempt 1: scoped production Pages **PASS** for that predecessor revision only.

The current PASS does not erase the historical reload/persistence failures or establish a recurrence rate. Issues #120/#126 and reopened #335 remain relevant reliability work even though the exact-current-main release/browser gate is green.

## Protected RuntimeJournal accepted scope

Merged **#338** is no longer a candidate. It changed protected `RuntimeJournal` bytes and advanced `verifier/v3/factory_ownership_baseline.json` under an explicit protected-ownership sequence.

The accepted behavior is narrow: constructor schema/metadata initialization may retry genuine SQLite lock contention under the existing bounded writer-transaction budget because those writes are idempotent; unrelated operational errors and exhausted deadlines still raise. Focused regression coverage exercises transient busy recovery, non-contention immediate failure, and persistent-contention bounded failure.

This merge updates accepted repository bytes and the corresponding ownership pin. It does not imply universal runtime contention immunity, every-host Factory/M4 qualification, a new evidence-schema authority, or blanket trust-boundary qualification. Historical candidate failures and the earlier narrow/mobile regression observed on an older #338 head remain retained predecessor-head evidence rather than being rewritten.

## Qualification-v1 testing branch
Qualification-v1 remains an independent testing-branch evidence path and does not become current-main capability merely because branch lanes pass.

Open **#152** is now at exact testing-branch head **`6cede25215221ee425af539f9a2609c52392bd7c`** after merging current `main` into the qualification branch with the ownership union preserved. That head remains protected candidate evidence only; it is not accepted current-main Factory/M4 qualification.

Exact-head `RESIDUAL Qualification v1` run **`35481689839`, attempt 1, is FAIL**. The `deterministic` job failed at **`Full deterministic regression gate`** while the visible sibling qualification lanes, including discovery, exact-wheel/container artifacts, toxic-provider, protocol-fuzz, M4, browser, lifecycle, concurrency and related qualification jobs, produced retained artifacts and/or passed their own jobs. The deterministic evidence envelope is bound to source commit `6cede252...`, tree `ae96dc0b6f21177e49d8d8919b06f800744a8441`, result **FAIL**, `unknown_count: 0`; its retained artifact is `qualification-v1-deterministic-abd12fe6c411d511f98f0bd8c65c9b07523e744e`, artifact id `10595394763`, SHA-256 `b828a890be394bf0f0756f9cdbc65af83ec75fcb1af186aca1b0e5038d23378b`.

The retained deterministic log reports **17 failed / 1823 passed / 22 skipped / 387 subtests passed**. Every observed sandbox-startup failure in that retained log includes `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` on GitHub-hosted Ubuntu 24 (`ImageOS: ubuntu24`, Linux `6.17.0-1022-azure`). This establishes a runner/environment incompatibility for that exact run; it does **not** justify weakening production sandbox policy, skipping the deterministic gate, or converting the run to PASS.

Open **#355** is a focused repair candidate targeting `testing/qualification-v1`, not `main`, at exact head **`a2a95116b840483bae421b6f8e1338a151a42ec4`**. It changes only `.github/workflows/qualification-v1.yml` and `tests/qualification/test_full_suite_workflow_dependencies.py`: the deterministic job is pinned from `ubuntu-latest` to `ubuntu-22.04`, and provisioning gains a fail-closed bubblewrap capability probe exercising `--unshare-pid --unshare-net` plus regression assertions that the pin/probe remain present and `continue-on-error` remains absent. No runtime sandbox implementation, verifier authority, ownership baseline, protected Factory/M4 bytes, skip policy, or evidence schema is changed by #355.

Exact-head #355 `RESIDUAL Qualification v1` run **`35482158683`, attempt 1, is FAIL**. Its new provisioning/capability probe passes on Ubuntu 22 (`ImageOS: ubuntu22`, Linux `6.8.0-1064-azure`), and the retained deterministic evidence no longer contains the predecessor `RTM_NEWADDR` startup signature, but the full deterministic gate still fails: **9 failed / 1853 passed / 387 subtests passed, with `skip_count: 0`**. Eight failures are in `tests/enterprise/test_supplychain.py::TestSandbox` (including benign/allowlisted execution being stopped by the containment boundary and several denial tests observing a different fail-closed error string than expected); one is `tests/redteam/test_worker_attacks.py::TestSandboxEscapeAttempts::test_write_etc_hosts_attempt`, where the sandbox command printed `PWNED` and the test's denial assertion failed. That retained observation does **not** by itself establish that the host's `/etc/hosts` was modified; it establishes that the exact sandbox security regression did not observe the required denial. The deterministic evidence is bound to source `a2a95116...`, tree `69e7dbee9ed89cf23e90419df0f560ed26a12e79`, result **FAIL**, `unknown_count: 0`; retained artifact `qualification-v1-deterministic-7c4a07c2961d9d197878fc4816cfdfa265e96ff9`, artifact id `10596630391`, SHA-256 `e1cbe908812b60d7b6a33f54d27c10be464863a26ce6f051c091c7f6fed1e83e`.

On the same #355 exact head, Factory ownership, Control Plane, measured-evaluation binding, clean install, Controller/provider and Command Station workflows are **PASS**, while PR-Agent advisory is **FAIL**. The qualification repair is therefore **FAIL**, not PASS or UNKNOWN. The runner change removed the previously observed namespace-startup blocker but exposed a different retained deterministic failure set that now requires review/repair without weakening the sandbox gate.

Open **#356** is the focused product-path successor targeting #355 at exact head **`95ab297cb7a4b82a54fe81db11b0340d3ae030fe`**. It changes only `residual/sandbox/bwrap.py`, `residual/supplychain/sandbox.py`, `tests/test_sandbox.py`, and `tests/test_supplychain_sandbox_runtime.py`; it does not change ownership baselines, protected Factory/M4 bytes, verifier authority, evidence schemas, or skip policy. The candidate keeps the existing minimal bwrap runtime roots, chooses a jail-visible `/usr/bin/python3` for supply-chain execution instead of widening host mounts, and remounts only the synthetic sandbox root read-only after explicit mounts are constructed.

Exact-head #356 `RESIDUAL Qualification v1` run **`35484064567`, attempt 1, is PASS**. Its final manifest is bound to source commit `95ab297c...`, tree `c7c7d6f4d626af76a80809f587fa6f0c82e9728c`, contains all 25 required gates as **PASS**, has no missing gates, and records no gate skips or unknowns. The deterministic gate itself is **PASS** with **1865 passed / 387 subtests passed / 0 skipped**, `unknown_count: 0`; retained deterministic artifact `qualification-v1-deterministic-7b651be81050bff064b27c3ed90ec168eaf0c9fc`, artifact id `10596342910`, SHA-256 `ac1b5e7fef9fe9aa10e2bc6603f9306847ca215d40d6458dd83cc641529718af`. The final manifest artifact is `qualification-v1-final-7b651be81050bff064b27c3ed90ec168eaf0c9fc`, artifact id `10596218366`, SHA-256 `8889ef7b9c87c2cd7553dfedea951ecf42a42e01ec29c7a67b45ef84bc895fea`.

That qualification PASS is bounded to #356's exact head and does not make the candidate merge-ready by itself. On the same head, Control Plane, Factory ownership, measured-evaluation binding, clean install, Command Station, and PR-head GitHub Pages run **`35484064541`** are **PASS**, while **Controller/provider contracts run `35484064575` is FAIL** because its Python 3.13 matrix job `106007034610` fails at `Compile and test without model credentials`; Python 3.11 and 3.12 jobs pass. Successor #357 records the retained lower-level result as **1 failed / 1175 run / 22 skipped**, with the sole failure `RuntimeJournalWriterAdmissionTests.test_constructor_persistent_busy_is_bounded_and_fail_closed` observing one constructor `BEGIN` attempt where the test required more than one. That diagnosis does not rewrite #356: its exact-head required product lane remains **FAIL**. PR-Agent advisory is also **FAIL**. #356 therefore remains **UNACCEPTED / FAIL on required exact-head product CI** despite the scoped Qualification-v1 and Pages PASS results.

Open **#357** is the focused successor targeting #356 at exact head **`a18fdf2041f314b7285975e1bf621760f6a6fe35`**. It changes only `tests/test_release_stabilization_runtime_journal.py`: the 120 ms persistent-constructor-contention deadline and fail-closed bounds remain unchanged, while the test no longer requires a second `BEGIN` when the first initialization cycle can consume the whole budget on Python 3.13; the separate transient-contention test continues to pin retry behavior. #357 changes no RuntimeJournal implementation, timeout, verifier authority, Factory/M4 protected byte, ownership baseline, evidence schema, sandbox control, or qualification skip semantics.

On exact #357 head, `RESIDUAL Qualification v1` run **`35487109155`, attempt 1, is PASS** and retained artifacts include deterministic artifact id **`10598546143`**, SHA-256 **`badcfafe6ef5346af4d7be4fe501802f0e25994b1290c99a7577e8d7b45689ba`**, and final-manifest artifact id **`10598465702`**, SHA-256 **`d95e57cdea360fa777c9058c98d025fa3ffc00a6208df9c1ffc129d2f0dbcf0a`**. Controller/provider run **`35487109176` is PASS** across Python 3.11, 3.12, and 3.13, including the Python 3.13 `Compile and test without model credentials` step. Control Plane, Factory ownership, measured-evaluation binding, clean install, and Command Station workflows are also **PASS**; Vercel is **PASS** and the ordinary Aikido code scan is **PASS**, while Aikido deep review is **SKIPPED / unavailable** for exhausted credits. PR-Agent advisory run **`35487109150`, attempt 2, is PASS**, including the repository's `Verify substantive advisory review was published` step; attempt 1 remains historical **FAIL** evidence and is not erased. Protected maintainer approval remains **FAIL** because no exact-head write-capable human attestation exists, and there is still no submitted human review. #357 is therefore **UNACCEPTED** despite its scoped exact-head technical and advisory PASS results. Its PASS cannot be inherited by #356: if #357 is accepted into #356, the resulting #356 head requires fresh exact-head qualification and ordinary governance before any integration into #355.

The older `aeba9962...` run `35448856959` remains historical exact-revision **FAIL** evidence. Earlier #152, #355, and #356 results remain bound to their exact heads and are not inherited forward. The #357 PASS does not rewrite any predecessor failure and cannot be inherited by a later #356, #355, or #152 head after merge/rebase.

Because #152 still carries protected Factory/fixture/ownership evidence, it requires explicit trust-boundary review, fresh exact-head qualification after any accepted repair, protected maintainer approval, and merge authority. It must not be auto-merged or treated as accepted Factory/M4 qualification.

## Provider/runtime adapters, nested-runtime research, Wiki, agent onboarding, setup, and Station candidates

Open **#340** is the implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw provider/runtime adapter candidate. Its exact current head is **`faa315992500aeeb11d3ae045d68b2f0eb26d0cd`**. On that head, GitHub Pages, Control Plane, Factory ownership, clean install, and measured-evaluation acceptance binding are **PASS**, while Command Station and Controller/provider workflows are **FAIL**; protected maintainer approval is **FAIL**, and PR-Agent advisory is **FAIL**. The lower-level causes of the two product-test workflow failures are not established by this status summary and remain **UNKNOWN** here. #340 is therefore **UNACCEPTED / FAIL on required exact-head CI**, and no current-main provider capability or live-provider quality claim changes because of it.

Draft **#341**, `EXP-NESTED-SWARM-001`, contains the research/evaluation material split out of #340. It is explicitly **RESEARCH ONLY — DO NOT MERGE** in its current form. Staged definitions, adapters, or evidence contracts are availability only, not proof of nested-swarm benefit or accepted provider capability.

Draft **#344** remains **DRAFT / UNACCEPTED** at exact head **`1b5b183edc7fd78093f8140dddf9ecc4a4c0f1d0`**. It proposes Arena provider transport plus the local Arena-aligned paired benchmark scaffold **`AX-ARENA-01`**. At that exact head, Control Plane, Factory ownership, Controller/provider, clean install, measured-evaluation and Command Station workflows are **PASS**; protected maintainer approval is **FAIL**, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The repository does not claim official Agent Arena participation, an official Arena score, accepted Arena-provider capability, or comparative RESIDUAL-vs-control benefit from this branch. Its checked-in development fixture and benchmark apparatus remain availability only, not paper-facing outcome evidence.

Draft **#345** is a **DRAFT / UNACCEPTED** RESIDUAL Wiki + setup-agent candidate at exact head **`2a16fe4c05deea6a3f3827cb6f4c99ec2bf28408`**. It keeps `docs/` as the canonical documentation source while adding Station Wiki/search/viewer/grounded setup-agent surfaces and repository-shipped declarative setup skills. At that exact head, Control Plane, clean install, Factory ownership, measured-evaluation, Factory runtime evidence, Factory OS execution evidence, Command Station, Controller/provider contracts, and the PR-head GitHub Pages workflow are **PASS**; protected maintainer approval is **FAIL**, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. These branch-only results do not establish accepted current-main Wiki/setup-agent capability or authority to execute documentation-derived instructions.

Draft documentation-only **#346** adds an agent-first repository/wiki onboarding layer (`AGENTS.md`, wiki bootstrap/skills/operations/docs-map material, and a `docs/README.md` discoverability link) at exact head **`44f849c26720473355f76a633aeb567e5ca89c09`**. Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, Command Station, and Controller/provider workflows are **PASS**; protected maintainer approval and PR-Agent advisory are **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The branch is **DRAFT / UNACCEPTED** and intentionally remains separate from this current-status reconciliation; its navigation layer is not accepted-main documentation yet.

Open **#347** proposes persistent setup PATH configuration plus a native `residual start` command at exact head **`4bde4fcd8a25d956f0bb0bf21ca4ad53b6c05e30`**. Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, Factory runtime evidence, Command Station, Controller/provider contracts, and PR-head GitHub Pages are **PASS**. Protected maintainer approval is **FAIL** because no exact-head attestation exists, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The candidate is therefore **UNACCEPTED**; accepted-main setup behavior, `START-HERE.md`, and CLI launch semantics have not changed.

Open **#348** is a public-interface/documentation consistency repair at exact head **`f938fac8b20abae0fca4e47476a984b104aa3d83`**. It corrects the accepted-main public site command `residual run examples/demo.toml --json`, which does not match the CLI parser, to the parser-valid `residual run examples/incident/task.json --config examples/demo.toml`; it also proposes a live-state pointer for `docs/CURRENT_STATUS.md` so an old snapshot is not presented as current forever. On that exact head, Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, Command Station, Controller/provider contracts, PR-head GitHub Pages, and Vercel are **PASS**. Protected maintainer approval is **FAIL**. PR-Agent advisory run **`35466382557`**, attempt 2, is **PASS**, including the repository's substantive-advisory verification step; the earlier unavailable/failed advisory state is therefore historical and is not the current exact-head advisory result. Aikido's ordinary code check passed while its deep review was **SKIPPED / unavailable** because review credits were exhausted. Until #348 is accepted, the public-site CLI example on current `main` remains a known documentation/interface defect; #348 itself remains **UNACCEPTED** and its proposed status-document structure is not yet accepted-main documentation.

Draft **#349** proposes Shared Comms as project group chat and advisory planning context at exact head **`0abcf503e76bb89d8fd9c6cc22597ce2b9c3819f`**. The branch explicitly remains on **HOLD for merge while #152 qualification convergence owns the critical path**. On this newer exact head, Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, and PR-head GitHub Pages are **PASS**; Command Station and Controller/provider workflows are **FAIL**, protected maintainer approval is **FAIL**, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The current retained workflow summaries establish required product-CI failure but do not identify a reviewed lower-level invariant that would justify a stronger root-cause claim here, so that cause remains **UNKNOWN**. #349 is therefore **DRAFT / UNACCEPTED / FAIL on required exact-head product CI** and does not establish accepted Shared Comms, runner-chat, or planner-context capability on current `main`.

Open **#198** has been refreshed directly on exact current `main` as a safe `residual update` CLI candidate at exact head **`51cd31ad1dc4de082bdf96d37170b3425c3756e4`**. It proposes fail-closed fast-forward-only source updates and a bounded installed-package upgrade path, but accepted current main does not yet provide that command. On the exact head, Control Plane, Factory ownership, measured-evaluation binding, clean install, PR-Agent advisory, Command Station, Controller/provider, and PR-head GitHub Pages are **PASS**; protected maintainer approval is **FAIL**. Required Factory runtime evidence run **`35489733181` is FAIL** at `Baseline and Factory contracts`; the retained job shows `RuntimeJournalWriterAdmissionTests.test_constructor_persistent_busy_is_bounded_and_fail_closed` observing one constructor `BEGIN` attempt where the test required more than one. That is the same timing-test class addressed by #357, but #357's evidence does not transfer to #198. #198 therefore remains **UNACCEPTED / FAIL on required exact-head CI** until a changed exact head is freshly qualified.

Open issue **#358** specifies a broader Swarm Migration Control Plane for canonical Project State, exact StateDelta synchronization, durable capability/enrollment state, intelligence routing, experiment control, operator-effort accounting, recursive-development phases, contradiction detection, and continuous documentation/readiness loops. It is a specification, not accepted current-main capability. The specification explicitly keeps Station/Git/receipts/qualification/operator evidence authoritative, treats model synthesis as advisory, and says the migration must not automatically expand the current v1 critical path; implementation is to proceed in independently qualified slices.

Draft **#359** is the first bounded SM-01/SM-02/SM-03 implementation slice from #358 at exact head **`0fffc8d97d83b55c84cfa9aaed9973dd1e5bd41a`**. It adds canonical project-state/state-delta contracts plus a durable enrolled-runner/capability registry, but deliberately does **not** wire synchronization into `/api/worker/claim`: AUD-1 F2 has not yet supplied the runner-identity primitive required to make claim-time synchronization an actual identity boundary. On exact #359 head, measured-evaluation binding, Control Plane, Factory ownership, clean install, Controller/provider, Command Station, and PR-head GitHub Pages are **PASS**; protected maintainer approval and PR-Agent advisory are **FAIL**. #359 remains **DRAFT / HOLD / UNACCEPTED** and does not establish per-runner cryptographic authentication, cross-project isolation, or network-level claim-time sync.

Open documentation-only **#361** adds a proposed canonical Runtime Profile Loader contract at exact head **`6ec887f0d162ef06c4a097ccbc8f3955451e1712`**, touching only `docs/README.md` and `docs/station/RUNTIME-PROFILE-LOADER.md`. The new document is explicitly **Proposed / Backlog**: it defines generic profile discovery/selection/loading, lifecycle, fallback, capability/adaptor publication, health, shutdown, permission, and authority boundaries, with Omarchy as a proving profile rather than a Station dependency. It does **not** implement the loader or establish accepted Omarchy/runtime-profile capability. On the exact head, Control Plane, Factory ownership, clean install, measured-evaluation binding, Controller/provider contracts, Command Station, and PR-Agent advisory are **PASS**; PR-Agent run **`35494206340`** also passed its substantive-advisory verification step. Vercel is **PASS**, while protected maintainer approval is **FAIL**. #361 therefore remains **UNACCEPTED / specification-only**; no runtime, verifier, Factory/M4, evidence-schema, or acceptance authority changed.

## Accepted authority repair and retained stress evidence

Merged #288 closes product issue #208 with host-owned pre-dispatch budget/deadline admission and run-control-bound export eligibility. It changes current product behavior but does **not** rewrite frozen research evidence:

- #207 STRESS-B1 remains historical **FAIL**;
- #207 STRESS-B3 remains historical **FAIL**;
- #212 missing-usage remains historical **FAIL for accounting-before-authority**;
- bounded containment/recovery PASS cells remain PASS in their own scope.

A stronger present-tense claim that the repaired path prevents all affected authority-ordering failures remains **UNKNOWN pending repaired-path requalification**.

## Research Workbench

Draft **#323** remains unaccepted. #288 is accepted, satisfying its first prerequisite, but #323 still requires rebase and fresh qualification before the first authoritative M6-WB-001 trial.

- current #323 implementation: **UNACCEPTED / draft**;
- first authoritative M6-WB-001 trial: **BLOCKED / not run** pending rebase and fresh qualification;
- staged experiment definitions are availability only, not experiment evidence.

## Security and governance posture boundary

- **#320:** repository CSP/anti-clickjacking policy is accepted; production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328:** core source/runtime security hardening is accepted for its reviewed scope.
- **#330:** checkout credential-persistence hardening is accepted for its reviewed workflow scope.
- **#337:** PR-Agent advisory publication/concurrency hardening is accepted for its reviewed governance scope.
- **#338:** protected RuntimeJournal contention handling + ownership-pin advance is accepted for its reviewed scope; the PR-Agent advisory for the exact merge head was **FAIL / unavailable**, not PASS.
- **#353:** owner-authored AUD-1 convergence issue treats frozen `main@2f9dda38...` as subject to a P0 pre-release security gate. F1-F3 are recorded as **P0 BLOCKER** findings; F4 and F6 are required in the same P0 lane. No exact remediation candidate exists yet, so repair qualification is **UNKNOWN / pending**, while release convergence is **BLOCKED** under the declared gate sequence.
- **#354:** open governance-regression candidate at exact head **`e2327e870137f7b418a656d59311984940b57388`**. It adds gate-index tests, maintainer-approval parser hardening, and a new `verifier/v3/governance_integrity.json` manifest that pins governance-critical bytes; it does not change workflows or production code. Exact-head Factory ownership, Control Plane, measured-evaluation binding, clean install, Controller/provider and Command Station workflows are **PASS**, and Vercel is **PASS**. Protected maintainer approval is **FAIL** and PR-Agent advisory is **FAIL**. Its own release-convergence instruction is **DO NOT MERGE / HOLD** until #152 lands and new-main qualification completes. The new integrity manifest is therefore candidate trust-boundary material, not accepted-main authority.
- **#355:** open qualification-runner repair candidate against `testing/qualification-v1`, exact head **`a2a95116b840483bae421b6f8e1338a151a42ec4`**. The deterministic run's fail-closed bubblewrap capability probe passes on Ubuntu 22, but exact-head Qualification-v1 run `35482158683` is **FAIL** with a changed nine-test deterministic failure set. The predecessor `RTM_NEWADDR` runner-startup signature is absent, so the runner pin/probe moved the observed boundary rather than establishing PASS. The retained failures now include enterprise sandbox containment/result-contract failures and one red-team `/etc/hosts` denial assertion failure; no claim of host modification is made from that sandbox-local observation. The candidate still does not change runtime sandbox or protected Factory/M4 implementation/evidence schemas.
- **#356:** open product-path sandbox repair candidate at exact head **`95ab297cb7a4b82a54fe81db11b0340d3ae030fe`**. Exact-head Qualification-v1 run `35484064567` and PR-head Pages run `35484064541` are **PASS**, but required Controller/provider run `35484064575` is **FAIL** on Python 3.13. Successor #357 records the sole suite failure as the persistent-constructor-busy timing assertion described above. That diagnosis does not change #356's exact-head FAIL. PR-Agent advisory is **FAIL**; #356 remains **UNACCEPTED** until an accepted repair produces a new head that is freshly qualified.
- **#357:** open one-file test-instrumentation successor at exact head **`a18fdf2041f314b7285975e1bf621760f6a6fe35`**. Exact-head Qualification-v1 run `35487109155`, Controller/provider run `35487109176` across Python 3.11/3.12/3.13, Control Plane, Factory ownership, measured-evaluation binding, clean install, Command Station, Vercel, and PR-Agent advisory run `35487109150` attempt 2 are **PASS**; the PR-Agent workflow also passed its substantive-advisory verification step. Attempt 1 remains historical **FAIL** evidence. Protected maintainer approval remains **FAIL**, Aikido deep review is unavailable for exhausted credits, and no submitted human review exists. #357 is **UNACCEPTED**, and none of its PASS results transfer to #356/#355/#152 after integration without fresh exact-head qualification.
- blanket repository security or independent-review qualification: **not established**.

Issue #353 requires separate retained physical reconnect evidence for inside-window recovery and outside-window authority expiry; those claims must not be collapsed into a single reconnect PASS. Mason's future independent re-audit is necessary evidence for the declared convergence sequence but does not itself authorize merge.

Current Vercel deployment-rate-limit failures are infrastructure status and do not establish production response-header behavior one way or the other.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls failed closed as `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Accepted provider/session/bootstrap/publication changes and open provider candidates do not substitute for fresh live semantic evidence. Therefore:

- successful paid/live provider candidate→verifier→receipt execution on exact current main: **UNKNOWN / not established**;
- candidate correctness for the historical failed calls: **UNKNOWN**;
- model quality implied by Pages or provider-contract CI: **UNKNOWN / not established**.

The #186 iOS/WebKit fallback remains accepted only as a lightweight pre-boot route. Physical heavyweight-WebVM reliability and long-run recurrence/root cause under #120/#126/#335 remain **UNKNOWN / unqualified**.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a production-qualification manifest.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their reviewed scope. Merged #338 is a separate explicit protected sequence and must remain scoped to its reviewed RuntimeJournal constructor-admission behavior and ownership pin. Separate protected sequences and Qualification-v1 work remain independent evidence paths.

Documentation does not change Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, evidence schemas, provider authorization, or acceptance authority.

Namespace/capability-unavailable execution remains `BLOCKED`/`UNKNOWN`, never PASS by documentation.
## Retained research evidence

### AX-21 federated swarm dogfooding

Draft **#350** is a research-only contemporaneous log at exact head **`c82924ccce18808aa7eca39a439f4d2cee8fbf96`**. It adds only `docs/swarm/ax21-federated-dogfood-log.md` and records the active multi-host dogfooding campaign's reported enrollment state, operator-effort baseline, retained lifecycle observations, stale-buffered-instruction finding, post-expiry recovery friction, and proposed RES-UP follow-up experiments.

Those entries remain **reported research observations / apparatus**, not production qualification and not independently promoted to retained verified findings by this status summary. The research log itself requires preservation of the underlying command/output evidence before reported transport, enrollment, lifecycle, intervention-count, or performance observations can be treated as retained evidence. P1 is not complete until its explicit exit criteria are evidenced, including simultaneous enrollment, identity binding, transport interruption/reconnect, credential rotation with old-credential invalidation, and a frozen operator-effort ledger.

On exact #350 head `c82924cc...`, Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, Controller/provider contracts, and Command Station workflows are **PASS**; Vercel is **PASS**. Protected maintainer approval is **FAIL** for lack of exact-head attestation, and PR-Agent advisory is **FAIL**. #350 therefore remains **DRAFT / UNACCEPTED** and does not change accepted current-main capability, Factory/M4 qualification, or general swarm-efficiency conclusions.

Open **#360** is a documentation/research-only AX-21 pre-release baseline candidate at exact head **`28b497c6f3c7e2afeabcaabb9d3460d74d134ca0`**. It adds only `docs/swarm/ax-21-pre-release-baseline.md`, preserving reported pre-release findings, the P5 operator-friction baseline, threats to validity, follow-on research tracks, and candidate `AX-21-BASELINE-R0` freeze criteria. Exact-head measured-evaluation binding, Factory ownership, Control Plane, clean install, PR-Agent advisory, Controller/provider, and Command Station workflows are **PASS**; protected maintainer approval is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. #360 is therefore **UNACCEPTED / research-only**. Its hypotheses and observed coordination/friction findings are preliminary research evidence, not production qualification; the document explicitly does not establish autonomous recursive development or general system security, and `AX-21-BASELINE-R0` remains only a candidate freeze pending the release-tagged reproduction and evidence manifest.

### FreeLLMAPI provider-candidate research

Open issue **#351** is a **RES-UP candidate in the research/provider lane, not a P1 blocker**. It records a LEGION setup/compatibility evaluation of FreeLLMAPI as an optional inference gateway and explicitly keeps the gateway outside the RESIDUAL trust boundary. The report states that no RESIDUAL worker, Station, drill, or tunnel integration was performed; observed OpenAI-compatible request/response behavior and two anonymous `model: auto` completions support a follow-on integration experiment only, not production qualification, privacy suitability, verifier authority, or accepted provider capability.

Draft documentation-only **#352** retains that experiment at exact head **`b95ae11abed72f48ccee1d3750b1c85c75eb9a2e`**. Its checked-in research record requires requested-route versus observed-route provenance, fail-closed treatment when route identity required by an experiment is unavailable, explicit privacy-policy metadata, a negative-path/fallback acceptance matrix, and a bounded economics/routing comparison. Those are proposed integration/evaluation requirements, not current-main behavior. On exact #352 head, Factory ownership, Control Plane, measured-evaluation acceptance binding, clean install, Controller/provider contracts, and Command Station workflows are **PASS**; Vercel is **PASS**. Protected maintainer approval and PR-Agent advisory are **FAIL**. #352 therefore remains **DRAFT / UNACCEPTED / research-only** and changes neither P1 state nor production-readiness claims.

The M6 record remains deliberately mixed:

- #203 / M6-SPEC-001: **FAIL**;
- #204 / M6-SPEC-002: **FAIL**;
- #215 / M6-SPEC-003: **FAIL**;
- #217 / M6-SPEC-004: **FAIL**;
- #220 / M6-SPEC-006: bounded corrected-path **PASS**;
- #257 / M6-SPEC-007J: bounded **PASS at formal MeasurementGap admission**;
- #264: integrity-valid workflow/receipt with scientific conclusion **UNKNOWN**;
- #274 / 007S: bounded **PASS** for registry/receipt semantic-binding controls;
- #273/#277: retained provenance/planner **FAIL** cells.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its declared semantic/derivation admission gates are satisfied.

### M6-MESH-001

#319 retains one bounded real-model crossover pilot in which both sequential and two-call concurrent conditions passed their obligation checks and the observed mean wall time favored concurrency. The small three-repeat, one-host cell does not establish a durable or general performance benefit. General mesh/swarm efficiency therefore remains **UNKNOWN / not established**.

## Current priority gates

1. **Resolve the AUD-1 P0 convergence gate in #353 without weakening authority boundaries.** The declared release sequence is implementation → ten adversarial regressions → ordinary CI → two separately retained physical F6 reconnect cases → Mason independent re-audit → exact-head qualification → owner review/attestation → merge → authoritative new-main qualification. Until that evidence exists, release convergence remains **BLOCKED**; no future candidate may inherit a PASS from the frozen baseline.
2. **Preserve the exact-current-main Pages PASS without broadening it.** Run `35452581203` attempt 1 is authoritative for `2f9dda38...`; predecessor FAILs remain evidence. Continue #120/#126/#335 reliability work without treating one green revision as long-run reliability proof.
3. **Carry #152 qualification convergence through the #355 → #356 → #357 repair chain without rewriting retained evidence.** Exact `6cede252...` run `35481689839` remains **FAIL** with the Ubuntu-24 `RTM_NEWADDR` startup signature. Exact #355 head `a2a95116...` removes that startup signature but run `35482158683` remains **FAIL** on nine deterministic sandbox/security regressions. Exact #356 head `95ab297c...` has a scoped Qualification-v1 and PR-head Pages **PASS**, but required Controller/provider CI remains **FAIL** on its Python 3.13 timing assertion. Exact #357 head `a18fdf20...` changes only that test instrumentation and has scoped Qualification-v1, Controller/provider, and PR-Agent substantive-advisory **PASS**, but protected maintainer approval remains **FAIL** and no submitted human review exists. Do not transfer #357 evidence backward: accept/review #357 only under its own governance, then freshly qualify the resulting #356 head; only after #356's own required gates pass should it move into #355, which must then be freshly qualified before any integration into #152. Preserve every predecessor FAIL/PASS as revision-bound evidence.
4. **Keep #354 governance tightening on HOLD until its declared release-convergence prerequisites are satisfied.** Its exact-head technical CI is green in the checked lanes and Vercel is PASS, but maintainer approval and PR-Agent advisory are FAIL; its governance-integrity manifest and parser-hardening tests are candidate trust-boundary material, not accepted main.
5. **Keep #340, #341, #344, #345, #346, #347, #348, #349, #350 and #352 separated and bounded; keep #351 research-only.** #340 is unaccepted and currently FAIL on required exact-head Command Station/provider CI; #341 is draft research-only nested-runtime work; #344 is a draft Arena-provider plus Arena-aligned benchmark scaffold; #345 is a draft Wiki/setup-agent candidate; #346 is draft docs-only agent/wiki onboarding; #347 is an unaccepted setup/`residual start` candidate; #348 is an unaccepted public-interface/current-status repair whose substantive PR-Agent advisory now PASSes but which still lacks protected maintainer approval; #349 is a draft/HOLD Shared Comms candidate with required product-CI failures; #350 is a draft research-only AX-21 dogfooding log whose reported observations are not production qualification or general swarm-efficiency proof; #351/#352 are FreeLLMAPI research/provider-candidate work that does not establish an accepted gateway integration, privacy suitability, or production readiness. None changes accepted current-main capability, setup semantics, documentation authority, or scientific conclusions until its own governance/evidence path is satisfied.
6. **Repair and requalify current exact-head product-test failures** before treating #340 or #349 as merge-ready; #356 remains a retained exact-head product-CI FAIL until #357 is accepted into it and that new #356 head is freshly qualified.
7. **Resolve the accepted-main public CLI example defect through #348 or an equivalent reviewed repair** before presenting that homepage command as valid current behavior.
8. **Requalify repaired authority ordering** against accepted #288 before broadening budget/unknown-usage/release-ordering claims.
9. **Rebase/requalify #323** before M6-WB-001 can run authoritatively.
10. **Validate #320 in production** before calling production CSP/anti-clickjacking response-header remediation PASS.
11. **Retain fresh live-provider semantic evidence** or keep exact-current-main paid/live provider success UNKNOWN.
12. **Complete blank-environment, recovery/host-loss, elapsed-soak and physical/mobile reliability work** without broadening bounded results.
13. **Keep research claims bounded.** General recursive self-improvement and general mesh efficiency remain UNKNOWN; M6-008 remains BLOCKED. AX-21 reported live-session observations remain research-only until the underlying evidence bundle and phase exit criteria are preserved and checked. FreeLLMAPI compatibility/setup observations remain research evidence only until an actual RESIDUAL integration is implemented and qualified.
14. **Retain governance gaps explicitly.** #338's failed PR-Agent advisory due provider-credit exhaustion is not substantive review evidence; open/draft candidates with failed approval/advisory gates remain unaccepted regardless of scoped technical greens.
15. **Keep refreshed #198 fail-closed and exact-head-bound.** Its source/update-path candidate is unaccepted because Factory runtime evidence run `35489733181` is **FAIL** on the persistent-constructor-busy timing assertion. #357's PASS does not qualify #198; any integrated repair requires a changed head and fresh exact-head CI/attestation before the update command can be treated as accepted behavior.
16. **Treat #358/#359 as migration architecture, not current-main authority.** #358 is a specification and #359 is a DRAFT/HOLD contract foundation. Do not wire or claim claim-time state synchronization until AUD-1 F2 establishes a runner-identity boundary; exact #359 technical greens do not establish per-runner authentication or cross-project isolation.
17. **Keep #360 as research-only baseline preservation.** Its AX-21 findings and P5 friction baseline remain preliminary/reported research evidence; maintainer approval is FAIL and Vercel is rate-limited. `AX-21-BASELINE-R0` remains a candidate freeze until the release-tagged reproduction/evidence manifest satisfies the document's own freeze criteria.
18. **Keep #361 as a proposed runtime-profile contract, not implemented capability.** Its docs-only exact head has the checked repository workflows, substantive PR-Agent advisory, and Vercel **PASS**, but protected maintainer approval is **FAIL**. Omarchy remains a proving profile in a proposed contract; no loader/runtime-profile behavior is accepted on `main` until a separately implemented and qualified candidate exists.
