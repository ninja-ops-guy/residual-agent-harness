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

Open **#152** has advanced five commits beyond the previously evaluated `aeba9962918c3659693e1efcd5603275cfb77cb4` head and is now at exact testing-branch head **`061910c56b23c58c064952a6414f0b5eb54baea6`**. The current head changes Factory source, protected expected-Factory fixture bytes, `tests/factory/ownership_baseline.json`, and qualification/runtime-gate material.

At this check, no exact-head workflow run or commit-status result had been published for `061910c5...`. Current exact-head Qualification-v1 status is therefore **UNKNOWN / pending**, not inherited PASS or FAIL.

The predecessor `aeba9962...` remains retained exact-revision evidence: `RESIDUAL Qualification v1` run **`35448856959` attempt 1 was FAIL**. On that predecessor head, bubblewrap sandbox provisioning, qualification self-tests, toxic-provider, M4, discovery, protocol fuzz, concurrency, browser, active-workload, fault-injection, macOS/Windows lifecycle and the other visible sibling lanes passed, while the required deterministic job failed at `Full deterministic regression gate`, causing the fail-closed aggregate to fail. The retained summary did not identify the lower-level deterministic invariant, so that cause remains **UNKNOWN**.

Because current #152 moves protected Factory/fixture/ownership evidence, it requires explicit trust-boundary review, fresh exact-head qualification, protected maintainer approval, and merge authority. It must not be auto-merged or treated as accepted Factory/M4 qualification. Earlier #152 results remain historical exact-head evidence only.

## Provider/runtime adapters, nested-runtime research, Wiki, agent onboarding, setup, and Station candidates

Open **#340** is the implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw provider/runtime adapter candidate. Its exact current head is **`faa315992500aeeb11d3ae045d68b2f0eb26d0cd`**. On that head, GitHub Pages, Control Plane, Factory ownership, clean install, and measured-evaluation acceptance binding are **PASS**, while Command Station and Controller/provider workflows are **FAIL**; protected maintainer approval is **FAIL**, and PR-Agent advisory is **FAIL**. The lower-level causes of the two product-test workflow failures are not established by this status summary and remain **UNKNOWN** here. #340 is therefore **UNACCEPTED / FAIL on required exact-head CI**, and no current-main provider capability or live-provider quality claim changes because of it.

Draft **#341**, `EXP-NESTED-SWARM-001`, contains the research/evaluation material split out of #340. It is explicitly **RESEARCH ONLY — DO NOT MERGE** in its current form. Staged definitions, adapters, or evidence contracts are availability only, not proof of nested-swarm benefit or accepted provider capability.

Draft **#344** remains **DRAFT / UNACCEPTED** at exact head **`1b5b183edc7fd78093f8140dddf9ecc4a4c0f1d0`**. It proposes Arena provider transport plus the local Arena-aligned paired benchmark scaffold **`AX-ARENA-01`**. At that exact head, Control Plane, Factory ownership, Controller/provider, clean install, measured-evaluation and Command Station workflows are **PASS**; protected maintainer approval is **FAIL**, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The repository does not claim official Agent Arena participation, an official Arena score, accepted Arena-provider capability, or comparative RESIDUAL-vs-control benefit from this branch. Its checked-in development fixture and benchmark apparatus remain availability only, not paper-facing outcome evidence.

Draft **#345** is a **DRAFT / UNACCEPTED** RESIDUAL Wiki + setup-agent candidate at exact head **`2a16fe4c05deea6a3f3827cb6f4c99ec2bf28408`**. It keeps `docs/` as the canonical documentation source while adding Station Wiki/search/viewer/grounded setup-agent surfaces and repository-shipped declarative setup skills. At that exact head, Control Plane, clean install, Factory ownership, measured-evaluation, Factory runtime evidence, Factory OS execution evidence, Command Station, Controller/provider contracts, and the PR-head GitHub Pages workflow are **PASS**; protected maintainer approval is **FAIL**, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. These branch-only results do not establish accepted current-main Wiki/setup-agent capability or authority to execute documentation-derived instructions.

Draft documentation-only **#346** adds an agent-first repository/wiki onboarding layer (`AGENTS.md`, wiki bootstrap/skills/operations/docs-map material, and a `docs/README.md` discoverability link) at exact head **`44f849c26720473355f76a633aeb567e5ca89c09`**. Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, Command Station, and Controller/provider workflows are **PASS**; protected maintainer approval and PR-Agent advisory are **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The branch is **DRAFT / UNACCEPTED** and intentionally remains separate from this current-status reconciliation; its navigation layer is not accepted-main documentation yet.

Open **#347** proposes persistent setup PATH configuration plus a native `residual start` command at exact head **`4bde4fcd8a25d956f0bb0bf21ca4ad53b6c05e30`**. Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, Factory runtime evidence, Command Station, Controller/provider contracts, and PR-head GitHub Pages are **PASS**. Protected maintainer approval is **FAIL** because no exact-head attestation exists, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The candidate is therefore **UNACCEPTED**; accepted-main setup behavior, `START-HERE.md`, and CLI launch semantics have not changed.

Open **#348** is a public-interface/documentation consistency repair at exact head **`f938fac8b20abae0fca4e47476a984b104aa3d83`**. It corrects the accepted-main public site command `residual run examples/demo.toml --json`, which does not match the CLI parser, to the parser-valid `residual run examples/incident/task.json --config examples/demo.toml`; it also proposes a live-state pointer for `docs/CURRENT_STATUS.md` so an old snapshot is not presented as current forever. On that exact head, Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, Command Station, Controller/provider contracts, PR-head GitHub Pages, and Vercel are **PASS**. Protected maintainer approval is **FAIL** and PR-Agent advisory is **FAIL**. Aikido's ordinary code check passed while its deep review was **SKIPPED / unavailable** because review credits were exhausted. Until #348 is accepted, the public-site CLI example on current `main` remains a known documentation/interface defect; #348 itself remains **UNACCEPTED** and its proposed status-document structure is not yet accepted-main documentation.

Draft **#349** proposes Shared Comms as project group chat and advisory planning context at exact head **`0abcf503e76bb89d8fd9c6cc22597ce2b9c3819f`**. The branch explicitly remains on **HOLD for merge while #152 qualification convergence owns the critical path**. On this newer exact head, Control Plane, Factory ownership, clean install, measured-evaluation acceptance binding, and PR-head GitHub Pages are **PASS**; Command Station and Controller/provider workflows are **FAIL**, protected maintainer approval is **FAIL**, PR-Agent advisory is **FAIL**, and Vercel is **FAIL due deployment rate limiting**. The current retained workflow summaries establish required product-CI failure but do not identify a reviewed lower-level invariant that would justify a stronger root-cause claim here, so that cause remains **UNKNOWN**. #349 is therefore **DRAFT / UNACCEPTED / FAIL on required exact-head product CI** and does not establish accepted Shared Comms, runner-chat, or planner-context capability on current `main`.

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
3. **Freshly qualify and explicitly review #152's current protected head.** Exact head `061910c5...` changes Factory source, expected-Factory fixture bytes and the ownership baseline, so its present status is UNKNOWN until exact-head evidence is published. Preserve predecessor `aeba9962...` run `35448856959` as historical FAIL evidence rather than inheriting it onto the new head.
4. **Keep #354 governance tightening on HOLD until its declared release-convergence prerequisites are satisfied.** Its exact-head technical CI is green in the checked lanes and Vercel is PASS, but maintainer approval and PR-Agent advisory are FAIL; its governance-integrity manifest and parser-hardening tests are candidate trust-boundary material, not accepted main.
5. **Keep #340, #341, #344, #345, #346, #347, #348, #349, #350 and #352 separated and bounded; keep #351 research-only.** #340 is unaccepted and currently FAIL on required exact-head Command Station/provider CI; #341 is draft research-only nested-runtime work; #344 is a draft Arena-provider plus Arena-aligned benchmark scaffold; #345 is a draft Wiki/setup-agent candidate; #346 is draft docs-only agent/wiki onboarding; #347 is an unaccepted setup/`residual start` candidate; #348 is an unaccepted public-interface/current-status repair; #349 is a draft/HOLD Shared Comms candidate with required product-CI failures; #350 is a draft research-only AX-21 dogfooding log whose reported observations are not production qualification or general swarm-efficiency proof; #351/#352 are FreeLLMAPI research/provider-candidate work that does not establish an accepted gateway integration, privacy suitability, or production readiness. None changes accepted current-main capability, setup semantics, documentation authority, or scientific conclusions until its own governance/evidence path is satisfied.
6. **Repair and requalify current exact-head product-test failures** before treating #340 or #349 as merge-ready.
7. **Resolve the accepted-main public CLI example defect through #348 or an equivalent reviewed repair** before presenting that homepage command as valid current behavior.
8. **Requalify repaired authority ordering** against accepted #288 before broadening budget/unknown-usage/release-ordering claims.
9. **Rebase/requalify #323** before M6-WB-001 can run authoritatively.
10. **Validate #320 in production** before calling production CSP/anti-clickjacking response-header remediation PASS.
11. **Retain fresh live-provider semantic evidence** or keep exact-current-main paid/live provider success UNKNOWN.
12. **Complete blank-environment, recovery/host-loss, elapsed-soak and physical/mobile reliability work** without broadening bounded results.
13. **Keep research claims bounded.** General recursive self-improvement and general mesh efficiency remain UNKNOWN; M6-008 remains BLOCKED. AX-21 reported live-session observations remain research-only until the underlying evidence bundle and phase exit criteria are preserved and checked. FreeLLMAPI compatibility/setup observations remain research evidence only until an actual RESIDUAL integration is implemented and qualified.
14. **Retain governance gaps explicitly.** #338's failed PR-Agent advisory due provider-credit exhaustion is not substantive review evidence; open/draft candidates with failed approval/advisory gates remain unaccepted regardless of scoped technical greens.
