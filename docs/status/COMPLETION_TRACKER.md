# Residual 1.0 + Experimental Release 1 completion tracker

Target: Residual 1.0 plus a completed Experimental Release 1 (ER1).
A credible negative or inconclusive experimental result is acceptable; favorable
hypothesis results are not a release requirement.

Snapshot: 2026-09-15, main `eefee6ac005c93278f483e002e38a768920f0fae`.
This reviewed tracker is delivered in PR #107. Refresh evidence before changing
a gate to PASS. Merged code, passing branch tests and completed release
qualification are different states.

## Scope policy for this completion plan

Freeze new planners, agent types, providers, dashboards, swarm types and
architectural abstractions. Allow work that closes a gate, fixes a defect,
improves onboarding/the canonical demo, or is required by the frozen experiment.
This policy is recorded for lane adoption; it is not enforced by GitHub settings.
Demo ownership remains in the existing demo thread.

## Already completed prerequisites

| Prerequisite | Verified disposition | Remaining boundary |
| --- | --- | --- |
| M4 code-hardening closure | [#81](https://github.com/ninja-ops-guy/residual-agent-harness/pull/81) merged | Capable-runner qualification and later boundary changes still need evidence |
| Frozen evaluation apparatus | [#86](https://github.com/ninja-ops-guy/residual-agent-harness/pull/86) merged | A framework is not a frozen live ER1 protocol or completed experiment |
| Workflow activation | [#101](https://github.com/ninja-ops-guy/residual-agent-harness/pull/101) merged | Complete required-check coverage and independent approval policy |
| Termination provenance tooling | [#96](https://github.com/ninja-ops-guy/residual-agent-harness/pull/96) merged | Runtime failures and #108 review blockers remain open |
| Clean-install tooling | [#100](https://github.com/ninja-ops-guy/residual-agent-harness/pull/100) merged | Blank-VM RC qualification still required |
| Measured acceptance binding | [#103](https://github.com/ninja-ops-guy/residual-agent-harness/pull/103) merged | Workflow activation overlaps #106/#107; real boundary qualification remains |
| WebVM/browser publication work | [#98](https://github.com/ninja-ops-guy/residual-agent-harness/pull/98) merged | Verify the final canonical demonstration at its deployed revision |
| Mission Control v1 | [#104](https://github.com/ninja-ops-guy/residual-agent-harness/pull/104) merged | Demo development and final user-journey acceptance remain with owner |
| Main branch protection | Active ruleset 23436488, 12 required checks, strict up-to-date validation, no bypass | Approving review count is 0; current-status and measured-eval-binding are not required |

Do not queue #101 or #96 for merger again. Older #69/#70/#71 are closed;
review their replacement work rather than rebasing those closed branches blindly.
Thirty open PRs remain at this snapshot. No tags were returned by Git's remote
tag listing, and the GitHub releases collection was empty.

## Reviewed 17-step plan

| ID | Step | Current state | Evidence already present / next acceptance condition | Owner / dependencies |
| --- | --- | --- | --- | --- |
| C01 | Freeze scope | POLICY DOCUMENTED; adoption pending | Use the policy above and flag out-of-scope requests; this PR does not globally control other threads | Owner + all lanes; start now |
| C02 | Converge PR board | PARTIAL | #101/#96 landed; #97/#94/#93 remain open. Resolve #106/#107 overlap. Classify and salvage old stacks; close only after explicit disposition preserves unique work | Backlog lane; no need to delay runner/corpus preparation |
| C03 | Qualify M4 | BLOCKED | #81 code exists; #88 remains open. Execute every mandatory security case on a capable runner with zero capability skips, bound to accepted code/schema | Runner lane + independent reviewer; after relevant #108 repairs |
| C04 | Finish Swarm 3 | PARTIAL / REPAIR BLOCKED | #96 already merged. #108 has unresolved production review and retained CI failure; see incident ledger below. Retain contention evidence and UNKNOWN attribution | Runtime implementer + separate reviewer |
| C05 | Qualify distributed/runtime behavior | PREPARATION / BLOCKED | #97 regressions await integration. Execute real-process concurrency, loss/restart/replay/cleanup/network cases, then 24h and 72h soak | Runtime/recovery lane; accepted candidate and isolated infrastructure |
| C06 | Port principal Factory benchmarks | PENDING RECONCILIATION | Salvage #26/#38/#46/#52/#54/#56 onto current Factory. Preserve FB001-FB004 progression and whole-project completion focus | Benchmark owner designated through backlog lane |
| C07 | Freeze ER1 protocol | PREPARATION | #86/#103 merged; #90/#91 drafts overlap. Freeze model/configuration, code/verifiers, budgets, repetitions, stopping rules, analysis and exclusions before confirmatory results | Science lane + independent protocol review |
| C08 | Acquire held-out corpus | PREPARATION; independent corpus not evidenced | Reconcile draft corpora, prove provenance/holdout and hidden graders, hash tasks/splits. 60-100 tasks across at least four families is a provisional target, not proof of adequate statistical precision | Corpus/science lane; start now, finalize before C07 |
| C09 | Fixed-model R0-R5 | NOT EVIDENCED | Run the frozen comparison and retain raw candidate outcomes, coverage, accepted correctness, AER/false rejection/FCR, complete compute cost, latency and throughput | Cleared trust/experiment gates + C07/C08 |
| C10 | Reliability degradation | NOT EVIDENCED | Freeze degradation mechanism and levels. Report realized worker correctness vs accepted correctness alongside coverage and uncertainty; also distinguish this from substituting different models | Science lane; preregister before results |
| C11 | Live fault injection | DEVELOPMENT EVIDENCE ONLY | Existing M4 trust fixtures are not the live campaign. Prove each intended fault was exercised and whether it reached accepted state; report invalid injections and UNKNOWN separately | Fault lane; accepted candidate/protocol, isolated resources |
| C12 | Matched-budget / heterogeneous experiments | PREPARATION; results not evidenced | #93 contains proposed accounting/observability work. Freeze comparisons, count verifier/retry/control compute, measure reliability-cost-latency frontier | Science/economics lane; shared corpus/protocol and budget authorization |
| C13 | Canonical demo | PARTIAL; substantial merged work | #98/#104 merged and current Pages/browser evidence passed. Final bad-candidate-to-receipt journey needs owner acceptance on deployed revision; preserve black/green design | Existing demo thread; parallel with science |
| C14 | Blank-machine RC | TOOLING COMPLETE; qualification not evidenced | #100 and current clean-install CI pass. Create RC1 only after candidate selection; independent installer exercises documented setup, recovery, restart, credentials, upgrade and cleanup on blank VM | Release lane; RC artifact and public docs |
| C15 | Freeze RC and final regression | NOT STARTED | Record RC commit/tree/package and rerun required integration, M4, runtime, benchmark, install, browser and soak gates against it | Integration coordinator; candidate stable |
| C16 | Paper from evidence | DRAFT/METHODS PRESENT; empirical results pending | Populate/reproduce Results from retained artifacts. Include uncertainty, negative findings, exclusions and UNKNOWNs; independent audit | Science/writing lane; may prepare methods now |
| C17 | Release 1.0 + ER1 | BLOCKED BY FINAL GATES | Publish only after all six gates below pass; experiment may reject or fail to resolve H1 credibly | Owner acceptance after independent review |

"Not evidenced" means no qualifying completed evidence was found in the
reviewed main, PR dispositions, retained main artifacts and release records.
It does not assert that no unpublished work exists in another thread.

## Six final gates

| Gate | Required result | Snapshot verdict / missing proof |
| --- | --- | --- |
| Core architecture | PASS on integrated RC, with independent review and enforced checks | AMBER: mechanisms present; latest main runtime tests fail; required approval count is 0 |
| M4 trust boundary | QUALIFIED with no skipped mandatory security capability tests | RED: capable-runner qualification outstanding; changes proposed in #108 need reviewed compatibility |
| Runtime/recovery | PASS plus completed 72h soak after clean shorter runs | RED: retained runtime failures, integration and elapsed soak evidence outstanding |
| Clean installation | PASS from genuinely blank VM on RC | AMBER: tooling and CI pass; independent blank-VM RC execution not evidenced |
| Canonical demo | PASS in real browser and guest on final deployed revision | AMBER: current browser/Pages jobs pass; full final narrative acceptance outstanding |
| ER1 | COMPLETE, reproducible and independently audited regardless of H1 outcome | RED: protocol/corpus reconciliation and confirmatory measurements outstanding |

**0/6 final release gates are fully evidenced at this snapshot.**
This is a release-gate count, not a claim that engineering progress is zero.
Earlier percentage estimates were planning judgments, not a measured
work-breakdown calculation; do not add them to this gate count.

## Retained current blockers

| Revision / run | Observation | Required treatment |
| --- | --- | --- |
| #108 head b3b2a5a; [Factory runtime evidence 34940491451](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34940491451), job 104287844727 | Lease-revocation test errors reading observations: SQLite database locked at PRAGMA synchronous=FULL | Reproduce/classify/fix without hiding the failure through retries |
| Main eefee6a; [controller/provider run 34958593443](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34958593443), job 104346500887, Python 3.12 | forbidden-tool test expected (VIOLATED, allowed_tools), observed (VIOLATED, lease_generation); 917 tests, one failure, 21 skips | Determine why the terminal reason differs; no causal conclusion from this assertion alone |
| Main eefee6a; [Command Station run 34958593479](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34958593479), job 104346500857, Python 3.13 | CLI real-backend test expected exit 0, observed 2; 917 tests, one failure, 21 skips | Classify retained process evidence; the accompanying runpy warning alone is not a demonstrated cause |
| #108 production review | Receipt schema compatibility, bounded lease I/O/resource enforcement, reap-timeout lifecycle, concurrent diagnostic attribution, fixture timeout consistency | Repair owner supplies genuine failing regression/reversion coverage; independent reviewer accepts final changes |
| Active main protection | No mandatory approving review; new status/binding checks optional | Maintainer requires at least one independent approval and adds the two checks, preserving existing protections |

Current-main ownership run 34958593498 and clean-install run 34958593422 passed.
Pages run 34958593448 passed; the browser and Docker jobs in Command Station
also passed. These results qualify their tested scope only.
Historical external SIGKILL attribution remains UNKNOWN unless its original
evidence establishes the cause; later instrumentation does not recover it.

## Corrections to sequencing and estimates

- Start runner provisioning, corpus acquisition, protocol preparation and release
  instructions during PR convergence. They need not wait for a pristine board.
- Select and freeze the candidate code before beginning any soak intended to
  qualify the release. Build RC1, perform blank-VM checks and run its other gates
  in parallel where dependencies permit. Material fixes require a new candidate
  and documented requalification.
- Define the final corpus and statistical plan before the ER1 freeze. Evaluate
  sample size/precision with accepted-task denominators and dependence between
  tasks/repetitions; 60-100 tasks may be insufficient for a strong reliability claim.
- Report coverage with conditional accepted correctness. Rejecting nearly every
  task must remain visible. Freeze FCR definitions and fault-exposure denominators.
- Keep ER1 immutable after freezing. Protocol-changing work gets a separately
  identified release/amendment under the declared policy, never a silent edit.
- Fault, degradation and matched-budget studies may execute in parallel when all
  were preregistered and resources are isolated; otherwise sequence them with
  explicit new protocol review. Preserve matched conditions and full compute cost.
- Seventy-two hours is elapsed observation, not parallelizable agent effort.
  Clean 24h followed by a separate 72h run requires at least 96h; alternatively
  predefine a continuous 72h run with a reviewed 24h checkpoint. Choose before execution.
- The listed 1-4 day durations are planning allowances, not commitments. Runner
  access, repair findings, corpus quality, provider limits and study size dominate
  the schedule. "Weeks" is plausible but not yet evidence-backed.
- A 30-day soak is a later production-maturity target; it is not an extra seventh
  gate in the agreed six-gate Residual 1.0 + ER1 definition.

## Immediate queue

1. Runtime owner repairs #108 plus classifies the fresh main failures; independent reviewer validates.
2. Backlog owner resolves #106/#107, #97/#94/#93 and benchmark-stack dispositions.
3. Maintainer completes review/check enforcement; runner and corpus lanes proceed now.
4. Coordinator assembles accepted changes, freezes an RC candidate and dispatches
   the parallel qualification lanes in [QUALIFICATION_EXECUTION_PLAN.md](QUALIFICATION_EXECUTION_PLAN.md).
5. Science owner freezes ER1 and runs it after the required trust/prerequisite gates pass.

Keep each tracker update bound to source revisions, run attempts, artifacts and
review dispositions. Opening or merging a PR alone cannot turn a release gate green.

