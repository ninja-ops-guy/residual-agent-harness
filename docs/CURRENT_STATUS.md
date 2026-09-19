# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@d89c5d940a32d8a7df4dd55e699c158fff5f615c`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`d89c5d940a32d8a7df4dd55e699c158fff5f615c`**, produced by merged **#336** on 2026-09-19 after merged **#337** landed the PR-Agent advisory-governance repair.

The two newly accepted changes are deliberately scoped:

- **#337** requires a substantive PR-Agent full-review marker and separates review/status concurrency so a bot failure/status comment cannot satisfy or cancel the legitimate advisory path.
- **#336** adds a guest-filesystem durability boundary before Mission Control/WebVM publishes reusable worker completion.

Neither merge broadens Factory/M4, verifier, evidence-schema, provider, or acceptance authority. Earlier accepted #307, #260, #288, #320, #328, and #330 retain their previously reviewed scope.

## Exact-current-main qualification

Accepted #276 requires every new `main` SHA to receive its own non-cancelling first production Pages attempt.

For exact current main `d89c5d94...`:

- production Pages run **`35449637725`**, attempt 1: **FAIL**;
- generated desktop+narrow artifact/browser proof: **PASS**;
- Pages deployment: **PASS**;
- published desktop exact-revision and real-guest execution: **PASS**;
- narrow boot/demo/warm reload/audit/provider boundary/build/follow-up/live transport/CLI→UI projection stages: observed **PASS** before the terminal failure;
- required narrow retained-evidence compound assertion: **FAIL**;
- retained live-proof artifact: **`webvm-live-proof-35449637725-1`**;
- artifact SHA-256: **`edd0d84e1270b71cc53039cae85e42041c06767c52039bb6c418a3ffffd62ff8`**;
- lower-level cause: **UNKNOWN**.

The failing command chains `test -s` existence checks for the live `answer.md`, build `artifacts/index.html`, and follow-up `artifacts/index.html`, followed by `verify_run(...)` for all three mission directories. Because those predicates were joined by `&&`, the retained attempt does **not** establish which individual existence/integrity predicate failed first. Do not attribute this failure to Puter, model quality, Factory/M4, provider transport, or another subsystem without stronger evidence.

The #336 `os.sync()` boundary is therefore **necessary but insufficient** for full narrow reload/evidence acceptance. The next changed-head repair should split the compound retained-evidence assertion into separately reported existence and `verify_run(...)` checks without weakening any requirement, then fix the first observed failing invariant. The unchanged `d89c5d94...` head must not be rerun merely to obtain green.

Predecessor evidence remains revision-bound: `0a675017...` run `35431634267` attempt 1 is a scoped **PASS** for that exact revision only; the `3bfa6aba...` and `e7b72ad...` production Pages attempts retain their exact-revision **FAIL** outcomes.

## Qualification-v1 testing branch

Qualification-v1 remains an independent testing-branch evidence path and does not become current-main capability merely because branch lanes pass.

Open **#152** has advanced to exact testing-branch head **`aeba9962918c3659693e1efcd5603275cfb77cb4`** through a sequence that adds real bubblewrap provisioning and tightens provider-mission/control-authority qualification.

The first exact-head `RESIDUAL Qualification v1` run on `aeba996...`, **`35448856959` attempt 1**, is **FAIL**. The retained job set shows:

- bubblewrap sandbox provisioning step: **PASS**;
- `qualification-selftests`: **PASS**;
- toxic-provider: **PASS**;
- M4: **PASS**;
- discovery, protocol fuzz, concurrency, browser, active-workload, fault-injection, macOS/Windows lifecycle and other visible sibling jobs: **PASS**;
- required deterministic job: **FAIL** at `Full deterministic regression gate`;
- fail-closed aggregate: **FAIL**.

The visible retained summary establishes that real sandbox provisioning itself now completed successfully, but it does not establish a new lower-level cause for the remaining deterministic regression failure. Preserve that cause as **UNKNOWN** until evidence identifies it. #152 remains open/unaccepted and its maintainer/advisory governance is unsatisfied. Predecessor #152 results remain historical exact-head evidence only.

## Protected RuntimeJournal candidate

Open **#338** is rebased onto current main and remains a separate protected trust-boundary candidate. It changes protected `RuntimeJournal` bytes and advances the Factory ownership-baseline pin while adding bounded write-admission behavior.

Accordingly #338 is **UNACCEPTED** until its exact current head satisfies all required technical/review/approval gates and receives explicit trust-boundary review. No automation should merge it. Sibling or predecessor green lanes do not override that requirement.

## Provider/runtime adapters and nested-runtime research

Open **#340** now contains the implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw provider/runtime adapter work. It is branch-only and **UNACCEPTED**; no current-main provider capability or live-provider quality claim changes because of it.

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

## Security posture boundary

- **#320:** repository CSP/anti-clickjacking policy is accepted; production Vercel response-header/Aikido validation remains **UNKNOWN / pending**.
- **#328:** core source/runtime security hardening is accepted for its reviewed scope.
- **#330:** checkout credential-persistence hardening is accepted for its reviewed workflow scope.
- **#337:** PR-Agent advisory publication/concurrency hardening is accepted for its reviewed governance scope.
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

Accepted #185/#187 protected-byte and ownership-baseline changes retain their reviewed scope. Separate protected sequences and Qualification-v1 work remain independent evidence paths. Documentation does not change Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, evidence schemas, provider authorization, or acceptance authority.

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

1. **Diagnose the current Pages failure without weakening acceptance.** Split the narrow retained-evidence compound assertion into independently reported existence and `verify_run(...)` checks on a changed head. Preserve `35449637725` attempt 1 as authoritative FAIL for `d89c5d94...`.
2. **Resolve #152's remaining deterministic Qualification-v1 FAIL.** Preserve `35448856959` attempt 1; real bubblewrap provisioning now passes, but the deterministic regression gate remains red and the lower-level cause is still UNKNOWN.
3. **Review #338 as a protected trust-boundary candidate.** Its RuntimeJournal/ownership-baseline changes must not be auto-merged.
4. **Keep #340 and #341 separated.** #340 is unaccepted implementation work; #341 is draft research-only work. Neither changes current-main capability or scientific conclusions.
5. **Requalify repaired authority ordering** against accepted #288 before broadening budget/unknown-usage/release-ordering claims.
6. **Rebase/requalify #323** before M6-WB-001 can run authoritatively.
7. **Validate #320 in production** before calling production CSP/anti-clickjacking response-header remediation PASS.
8. **Retain fresh live-provider semantic evidence** or keep exact-current-main paid/live provider success UNKNOWN.
9. **Complete blank-environment, recovery/host-loss, elapsed-soak and physical/mobile reliability work** without broadening bounded results.
10. **Keep research claims bounded.** General recursive self-improvement and general mesh efficiency remain UNKNOWN; M6-008 remains BLOCKED.

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