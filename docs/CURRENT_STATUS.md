# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@2f9dda3882f39c28a1c766859b1bf9579eea7911`._

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

Open **#152** remains at exact testing-branch head **`aeba9962918c3659693e1efcd5603275cfb77cb4`**. Its first exact-head `RESIDUAL Qualification v1` run **`35448856959` attempt 1 is FAIL**. The retained job set shows:

- bubblewrap sandbox provisioning step: **PASS**;
- `qualification-selftests`: **PASS**;
- toxic-provider: **PASS**;
- M4: **PASS**;
- discovery, protocol fuzz, concurrency, browser, active-workload, fault-injection, macOS/Windows lifecycle and other visible sibling jobs: **PASS**;
- required deterministic job: **FAIL** at `Full deterministic regression gate`;
- fail-closed aggregate: **FAIL**.

The visible retained summary establishes that real sandbox provisioning completed successfully, but it does not establish a lower-level cause for the remaining deterministic regression failure. Preserve that cause as **UNKNOWN** until evidence identifies it.

#152 remains open/unaccepted and must reconcile/requalify against current `main`, including the now-accepted #338 protected RuntimeJournal/ownership-baseline change, before any merge-readiness claim. Predecessor #152 results remain historical exact-head evidence only.

## Provider/runtime adapters and nested-runtime research

Open **#340** contains the implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw provider/runtime adapter work. It is branch-only and **UNACCEPTED**; no current-main provider capability or live-provider quality claim changes because of it.

Draft **#341**, `EXP-NESTED-SWARM-001`, contains the research/evaluation material split out of #340. It is explicitly **RESEARCH ONLY — DO NOT MERGE** in its current form. Staged definitions, adapters, or evidence contracts are availability only, not proof of nested-swarm benefit or accepted provider capability.

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
- blanket repository security or independent-review qualification: **not established**.

Current Vercel deployment-rate-limit failures are infrastructure status and do not establish production response-header behavior one way or the other.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls failed closed as `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Accepted provider/session/bootstrap/publication changes and open #340 do not substitute for fresh live semantic evidence. Therefore:

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

1. **Preserve the exact-current-main Pages PASS without broadening it.** Run `35452581203` attempt 1 is authoritative for `2f9dda38...`; predecessor FAILs remain evidence. Continue #120/#126/#335 reliability work without treating one green revision as long-run reliability proof.
2. **Resolve #152's remaining deterministic Qualification-v1 FAIL and reconcile it to current main.** Preserve `35448856959` attempt 1; real bubblewrap provisioning passes, but the deterministic regression gate remains red and the lower-level cause is still UNKNOWN. Requalification must include the accepted #338 protected RuntimeJournal/ownership-baseline state.
3. **Keep #340 and #341 separated.** #340 is unaccepted implementation work; #341 is draft research-only work. Neither changes current-main capability or scientific conclusions.
4. **Requalify repaired authority ordering** against accepted #288 before broadening budget/unknown-usage/release-ordering claims.
5. **Rebase/requalify #323** before M6-WB-001 can run authoritatively.
6. **Validate #320 in production** before calling production CSP/anti-clickjacking response-header remediation PASS.
7. **Retain fresh live-provider semantic evidence** or keep exact-current-main paid/live provider success UNKNOWN.
8. **Complete blank-environment, recovery/host-loss, elapsed-soak and physical/mobile reliability work** without broadening bounded results.
9. **Keep research claims bounded.** General recursive self-improvement and general mesh efficiency remain UNKNOWN; M6-008 remains BLOCKED.
10. **Retain governance gaps explicitly.** #338's failed PR-Agent advisory due provider-credit exhaustion is not substantive review evidence.

## Documentation scope for this reconciliation

Updated documentation is limited to `README.md`, `HARNESS.md`, `docs/CURRENT_STATUS.md`, `docs/research.md`, `docs/evaluation.md`, and `docs/roadmap/README.md`.

`START-HERE.md` and `implementation-status.yaml` remain intentionally unchanged because no accepted setup or implementation-presence claim changed.

## Claim discipline

- `PASS` applies only to the named revision/environment/gate.
- `FAIL` remains evidence after later repair.
- `UNKNOWN` means the required causal/evidentiary/qualification result is not established.
- `BLOCKED` means a required gate could not validly execute; it is not PASS.
- A research workflow can successfully retain a scenario-level FAIL; workflow success is not hypothesis success.
- PR-head or predecessor-main success is not accepted-current-main production evidence after the authoritative revision moves.
- A partial PASS inside a required multi-stage gate does not override that gate's terminal FAIL.
- A merge accepts repository bytes; it does not automatically establish every security, live-provider, physical-device, scientific, release, or independent-review claim associated with them.

The repository does not currently claim blanket production readiness, universal worker correctness, every-host M4 qualification, successful exact-current-main paid/live provider execution, completed blank-environment/recovery/soak qualification, physical heavyweight-WebVM iPhone reliability, production Vercel security-header validation, substantive PR-Agent advisory review for #338, general autonomous recursive self-improvement, general cooperative mesh efficiency, or proof of the central live-model reliability hypothesis.
