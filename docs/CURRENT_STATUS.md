# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@3bfa6abac719bb1ca5db225b32df347ae2afc079`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged **#330** on 2026-09-19. No newer production-main commit has landed in this check.

Recent accepted changes affecting the current boundary remain:

- **#307** — duplicate feature-branch CI fan-out repair while preserving PR qualification and non-cancelling production evidence;
- **#260** — provider bootstrap guard; bounded UI/transport behavior, not paid/live provider evidence;
- **#288 / #208** — accepted pre-dispatch Station budget/deadline authority and exact run-control-bound export eligibility; historical #207/#212 failures remain retained;
- **#320** — repository-side CSP/anti-clickjacking policy; production Vercel response-header validation remains **UNKNOWN / pending**;
- **#328** — scoped core execution/egress/XML hardening;
- **#330** — scoped GitHub Actions checkout credential-persistence hardening.

No accepted change above broadens Factory/M4, verifier, evidence-schema, provider, or acceptance authority.

## Exact-current-main qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For exact current main `3bfa6aba...`:

- production Pages run **`35437556200`**, attempt 1: **FAIL**;
- generated artifact/browser proof: **PASS**;
- deployment, served-revision identity, and desktop real-guest acceptance: **PASS**;
- required narrow/mobile Chromium acceptance: **FAIL** after the live guest reached shell-ready and multiple Workbench stages;
- retained live-proof artifact: **`10582812524`**, SHA-256 **`868ca31506d278a335ff95d3607adbd13c14edaec8b161c1b45ac013e7f7c8b8`**;
- lower-level cause: **UNKNOWN**. The retained evidence does not justify attributing the failure to #330, Puter/model quality, Factory/M4, or another subsystem.

The predecessor `0a675017...` production Pages run `35431634267`, attempt 1, remains a scoped **PASS for that exact revision only**. The earlier `e7b72ad...` production Pages run remains a retained **FAIL for that exact revision only**. Neither predecessor result is inherited by current main.

The current Pages failure is release/browser qualification evidence. It is not evidence of live provider/model quality failure, every-host M4 failure, or blanket product failure.

## Focused Pages repair and PR-review governance blocker

Open **#336** remains the focused changed-head durability repair. At exact head **`92aca285a9287b73787b552f87aaa42062e73ba4`**, its generated PR Pages proof `35438579639` attempt 1 is **PASS** and its named technical lanes are green. That evidence is branch-only. Protected maintainer approval is **FAIL**, and a substantive advisory review was not established.

Review of #336 exposed a separate governance defect: a provider-credit failure produced only `Failed to review PR`, while the old verifier could count a fresh bot failure/status comment as advisory-publication evidence; shared concurrency could also interfere with a legitimate review.

Open **#337** at exact head **`46e522b4437d42d68df170285bd3a93366808bd1`** is the focused governance repair. It requires the explicit full-review marker and separates review concurrency classes. It remains **UNACCEPTED** with PR Agent advisory and protected maintainer approval **FAIL**.

Therefore:

- current production `main@3bfa6aba...` Pages: **FAIL**;
- #336 generated branch Pages proof: **PASS** for its exact branch head only;
- #336 acceptance: **BLOCKED / HOLD** behind #337 plus fresh exact-head qualification and maintainer attestation;
- #337 acceptance: **FAIL / not accepted**;
- if #337 lands, #336 must reconcile to the resulting new main and regenerate merge-relevant exact-head evidence;
- if #336 later lands, that new main SHA still requires its own first authoritative production Pages PASS.

The retained production run `35437556200` remains evidence throughout the repair sequence.

## Qualification-v1 testing branch

Qualification-v1 remains an independent testing-branch evidence path and does not become current-main capability merely because a branch lane passes.

Merged **#339** moved open **#152** to exact testing-branch head **`19d3917079ee6f7105e78c88e2aae08d25ce4c13`**. #339 changes the provider-mission qualification path so export is bound through real run-control authority. It intentionally does not weaken or skip the fail-closed sandbox requirement.

The first exact-head `RESIDUAL Qualification v1` run on `19d391...`, **`35446710781` attempt 1**, is **FAIL**. The required failure set narrowed materially relative to predecessor head `11c0ac67...`:

- `qualification-selftests`: **PASS**;
- toxic-provider job: **PASS**;
- deterministic regression job: **FAIL** at the full deterministic regression gate.

The exact current run therefore remains an aggregate **FAIL**. The current visible workflow summary establishes the deterministic gate failure but does not, by itself, establish a new lower-level causal diagnosis. The predecessor `11c0ac67...` run `35443955204` remains historical exact-head **FAIL** evidence, including the retained hosted-runner observation that kernel-level sandbox isolation was unavailable and the earlier provider-mission-related selftest/toxic-provider failures. Those predecessor failures are not silently rewritten by #339.

For #152:

- exact-current testing-branch Qualification-v1: **FAIL**;
- accepted-main capability: **UNKNOWN / not established** because the PR remains open/unmerged;
- protected maintainer approval: **FAIL**;
- PR Agent advisory: **FAIL**;
- no branch PASS broadens exact-current-main Factory/M4 or release qualification.

## Protected RuntimeJournal contention candidate

Open **#338** is a separate protected trust-boundary candidate at exact head **`61986ecb56e35a845f2a66b64052b42b13e60be3`**. It changes protected `RuntimeJournal` bytes and advances the Factory ownership-baseline pin while adding bounded constructor write-admission retry for lock contention.

On that exact head, retained workflow state includes **PASS** for Factory ownership, Factory runtime/OS evidence, Control Plane, Controller/provider, Command Station, clean install, measured-evaluation binding, and the maintainer-approval gate. Generated PR Pages and PR Agent advisory are **FAIL**.

Accordingly #338 is **UNACCEPTED**. Its green scoped lanes do not override the failed required evidence, and because it touches protected Factory bytes plus the ownership baseline, it requires explicit trust-boundary review. It must not be auto-merged.

## Open provider/runtime adapter candidate

Open **#340** proposes Moonshot/Kimi API and Kimi Claw/OpenClaw provider/runtime adapters. It remains **UNACCEPTED / branch-only**. At current head `e527b1371e79a88d5efb7d46f37945fec796c5e1`, several technical lanes are **PASS**, production-style PR Pages qualification is still **in progress**, PR Agent advisory is **pending**, and protected maintainer approval is **FAIL**. No current-main live-provider capability or model-quality claim changes because of this candidate.

## Accepted authority repair and retained stress evidence

Merged #288 closes product issue #208 with host-owned pre-dispatch budget/deadline admission and run-control-bound export eligibility. It changes current product behavior but does **not** rewrite frozen research evidence:

- #207 STRESS-B1 remains historical **FAIL**;
- #207 STRESS-B3 remains historical **FAIL**;
- #212 missing-usage remains historical **FAIL for accounting-before-authority**;
- bounded containment/recovery PASS cells remain PASS in their own scope.

A stronger present-tense claim that the repaired path prevents all affected authority-ordering failures remains **UNKNOWN pending repaired-path requalification**.

## Research Workbench

Draft **#323** remains unaccepted. #288 is now accepted, satisfying its first prerequisite, but #323 still requires rebase and fresh qualification before the first authoritative M6-WB-001 trial.

- current #323 implementation: **UNACCEPTED / draft**;
- first authoritative M6-WB-001 trial: **BLOCKED / not run** pending rebase and fresh qualification;
- staged experiment definitions are availability only, not experiment evidence.

## Security posture boundary

- **#320:** repository CSP/anti-clickjacking policy is accepted; production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328:** core source/runtime security hardening is accepted for its reviewed scope.
- **#330:** checkout credential-persistence hardening is accepted for its reviewed workflow scope.
- **#324:** stale overlapping predecessor; must not be merged wholesale.
- blanket repository security qualification: **not established**.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls failed closed as `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Accepted provider/session/bootstrap/publication changes and open #340 do not substitute for fresh live semantic evidence. Therefore:

- successful paid/live provider candidate→verifier→receipt execution on exact current main: **UNKNOWN / not established**;
- candidate correctness for the historical failed calls: **UNKNOWN**;
- model quality implied by Pages or provider-contract CI: **UNKNOWN / not established**.

The #186 iOS/WebKit fallback remains accepted only as a lightweight pre-boot route. Physical heavyweight-WebVM reliability and long-run recurrence/root cause under #120/#126 remain **UNKNOWN / unqualified**.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a production-qualification manifest.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their reviewed scope. The separate protected sequences and Qualification-v1 work remain independent evidence paths. Documentation does not change Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, evidence schemas, provider authorization, or acceptance authority.

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

1. **Resolve #337 before accepting #336.** If #337 lands, reconcile/requalify #336 on the new exact main. Preserve production run `35437556200` attempt 1 as FAIL until a repaired merged-main SHA passes its own first authoritative Pages attempt.
2. **Resolve #152's remaining deterministic Qualification-v1 FAIL.** Preserve run `35446710781` attempt 1 and predecessor run `35443955204`; do not weaken the sandbox requirement or rerun an unchanged head merely for green.
3. **Review #338 as a protected trust-boundary candidate.** Its protected RuntimeJournal/ownership-baseline changes must not be auto-merged even with scoped PASS lanes.
4. **Requalify repaired authority ordering** against accepted #288 before broadening budget/unknown-usage/release-ordering claims.
5. **Rebase/requalify #323** before M6-WB-001 can run authoritatively.
6. **Validate #320 in production** before calling production CSP/anti-clickjacking response-header remediation PASS.
7. **Retain fresh live-provider semantic evidence** or keep exact-current-main paid/live provider success UNKNOWN; #340 is not accepted evidence.
8. **Complete blank-environment, recovery/host-loss, elapsed-soak and physical/mobile reliability work** without broadening bounded results.
9. **Keep research claims bounded.** General recursive self-improvement and general mesh efficiency remain UNKNOWN; M6-008 remains BLOCKED.

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
- A merge accepts repository bytes; it does not automatically establish every security, live-provider, physical-device, scientific, or release claim associated with them.

The repository does not currently claim blanket production readiness, universal worker correctness, every-host M4 qualification, successful exact-current-main paid/live provider execution, completed blank-environment/recovery/soak qualification, physical heavyweight-WebVM iPhone reliability, production Vercel security-header validation, general autonomous recursive self-improvement, general cooperative mesh efficiency, or proof of the central live-model reliability hypothesis.