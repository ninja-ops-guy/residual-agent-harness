# Residual 1.0 + Experimental Release 1 completion tracker

Target: Residual 1.0 plus a completed Experimental Release 1 (ER1).
A credible negative or inconclusive experimental result is acceptable; favorable
hypothesis results are not a release requirement.

Snapshot: 2026-09-15, main `1cf4e46c0ace8e3cdc76147ad4c7dc6480a9fb34`.
This reviewed tracker is delivered in PR #107. Refresh evidence before changing
a gate to PASS. Merged code, passing branch tests and completed release
qualification are different states.

Lane 2 follow-up, 2026-09-15: **#108 at `b127d000` is BLOCKED / REQUEST CHANGES**.
The independent review reproduced 12/12 original adversarial passes and caught
8/8 reversion attacks, but found five additional failing regression probes and
reproduced both CI failures. Local determinism is 19 passed, 2 failed, 7 skipped;
host capability prevents complete qualification. See the
[source-bound review and retained evidence](../../runs/reviews/pr108/b127d000/README.md).
Latest observed main is `326eb2a`, including #116; this observation does not
retroactively qualify the earlier PR integration or the final demo journey.

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
| Measured acceptance binding | #103 and activation [#106](https://github.com/ninja-ops-guy/residual-agent-harness/pull/106) merged | #106/#107 activation overlap resolved; require the new check in branch policy and qualify the real boundary |
| WebVM/browser publication work | [#98](https://github.com/ninja-ops-guy/residual-agent-harness/pull/98) merged | Verify the final canonical demonstration at its deployed revision |
| Mission Control | #104/#111/#112/#116 merged | Final deployed user-journey acceptance remains with demo owner |
| Main branch protection | Active ruleset 23436488, 12 required checks, strict up-to-date validation, no bypass | Approving review count is 0; current-status and measured-eval-binding are not required |

Do not queue #101 or #96 for merger again. Older #69/#70/#71 are closed;
review their replacement work rather than rebasing those closed branches blindly.
Thirty-two open PRs remain after this triage window (36 at its start). The
[full disposition ledger](PR_TRIAGE_2026-09-15.md) assigns seven Class A lanes
and 25 Class B salvage/deferred proposals, with exact file inventories and
the five completed merge/closure dispositions. No tags were returned by Git's remote
tag listing, and the GitHub releases collection was empty.

## Reviewed 17-step plan

| ID | Step | Current state | Evidence already present / next acceptance condition | Owner / dependencies |
| --- | --- | --- | --- | --- |
| C01 | Freeze scope | POLICY DOCUMENTED; adoption pending | Use the policy above and flag out-of-scope requests; this PR does not globally control other threads | Owner + all lanes; start now |
| C02 | Converge PR board | TRIAGE EXECUTED; integration ongoing | #106 merged; #22 closed; concurrent triage replaced #97 with #117 and closed #88/#114 into #109. 32 open proposals individually dispositioned; #93/#94 and benchmark salvage remain | Coordinator + lane owners; see full ledger |
| C03 | Qualify M4 | BLOCKED BY RUNNER | #109 at e873dd62 adds actual execution smoke and preserves the owner’s activated zero-skips workflow. Real hosted-runner probe reports BLOCKED/namespace unavailable. Closed #88/#114 are not gates to merge again | Runner lane + independent reviewer; accepted #108 boundary |
| C04 | Finish Swarm 3 | BLOCKED — independent review completed at b127d000 | #96 merged. #108 original battery 12/12 and eight reversion attacks pass review, but five new probes fail: payload budget, watchdog deadline under contention, reap recovery, diagnostic retention, total reader budget. Restore the stale v3 safety assertion to v2 to clear both CI failures; see the retained Lane 2 review | Runtime implementer repairs; separate reviewer rechecks new head and current-main integration |
| C05 | Qualify distributed/runtime behavior | BLOCKED BY THREE LOCAL FAILURES | #117 succeeds closed #97. Required pytest coverage now exposes missing process tracking, fencing through append and collision rejection (3 failed/60 passed locally). Repair and review before real concurrency/recovery and elapsed 24h/72h soak | Runtime/recovery lane; accepted candidate and isolated infrastructure |
| C06 | Port principal Factory benchmarks | PENDING RECONCILIATION | Salvage #26/#38/#46/#52/#54/#56 onto current Factory. Preserve FB001-FB004 progression and whole-project completion focus | Benchmark owner designated through backlog lane |
| C07 | Freeze ER1 protocol | RECONCILED SPECIFICATION DELIVERED in #110; execution blocked | #110 reconciles #90/#91 planning, pins the ladder/statistical rules and ledger, and preserves launch gates. Resolve the denominator and power-model review items below; implement/review adapters, analysis and launch enforcement; fill actual model/corpus identities before launch | Science lane + independent protocol review |
| C08 | Acquire held-out corpus | DEVELOPMENT TIERS PINNED; T3 blocked | #110 pins both 16-item development corpora and a confirmatory generation procedure. Actual T3 tasks/graders/hashes remain BLOCKED-UNTIL-GENERATED. Its proposed design uses 30-200 independent families, three tasks each: 90-600 tasks, replacing the earlier provisional 60-100 planning target if accepted | Corpus/science lane; power design must be resolved before selecting F |
| C09 | Fixed-model R0-R5 | NOT EVIDENCED | Run the frozen comparison and retain raw candidate outcomes, coverage, accepted correctness, AER/false rejection/FCR, complete compute cost, latency and throughput | Cleared trust/experiment gates + C07/C08 |
| C10 | Reliability degradation | NOT EVIDENCED | Freeze degradation mechanism and levels. Report realized worker correctness vs accepted correctness alongside coverage and uncertainty; also distinguish this from substituting different models | Science lane; preregister before results |
| C11 | Live fault injection | DEVELOPMENT EVIDENCE ONLY | Existing M4 trust fixtures are not the live campaign. Prove each intended fault was exercised and whether it reached accepted state; report invalid injections and UNKNOWN separately | Fault lane; accepted candidate/protocol, isolated resources |
| C12 | Matched-budget / heterogeneous experiments | PREPARATION; results not evidenced | #93 contains proposed accounting/observability work. Freeze comparisons, count verifier/retry/control compute, measure reliability-cost-latency frontier | Science/economics lane; shared corpus/protocol and budget authorization |
| C13 | Canonical demo | PARTIAL; substantial merged work | #98/#104 merged and current Pages/browser evidence passed. Final bad-candidate-to-receipt journey needs owner acceptance on deployed revision; preserve black/green design | Existing demo thread; parallel with science |
| C14 | Blank-machine RC | CORE TOOLING MERGED; procedure repairs needed | #100/clean-install CI exists. #115 review found truncation/completion defects in preparation tooling. Repair first, then an independent installer exercises setup, recovery, restart, credentials, upgrade and cleanup on a blank VM at RC1 | Release lane; reviewed procedures, RC artifact and public docs |
| C15 | Freeze RC and final regression | NOT STARTED | Record RC commit/tree/package and rerun required integration, M4, runtime, benchmark, install, browser and soak gates against it | Integration coordinator; candidate stable |
| C16 | Paper from evidence | DRAFT/METHODS PRESENT; empirical results pending | Populate/reproduce Results from retained artifacts. Include uncertainty, negative findings, exclusions and UNKNOWNs; independent audit | Science/writing lane; may prepare methods now |
| C17 | Release 1.0 + ER1 | BLOCKED BY FINAL GATES | Publish only after all six gates below pass; experiment may reject or fail to resolve H1 credibly | Owner acceptance after independent review |

"Not evidenced" means no qualifying completed evidence was found in the
reviewed main, PR dispositions, retained main artifacts and release records.
It does not assert that no unpublished work exists in another thread.

## Wave update: Priority 4 / PR #110

Reviewed [#110](https://github.com/ninja-ops-guy/residual-agent-harness/pull/110)
at head `41661a625656688538dd2bae1371fd90288283bd`. It is open/non-draft,
with five added documentation/manifest files. No runtime, launcher, analysis
implementation or executable test is added by that PR. Its planning deliverable
is present; this tracker does not certify its complete launch readiness.

Confirmed preparation: one R0-R5 ladder; development/confirmatory tier separation;
paired family-cluster analysis and fixed multiplicity family; per-run identity
and artifact requirements; a fail-closed specification for missing T3/adapters,
model/verifier identities and M4 qualification. #90/#91 retain distinct tooling
and code scope; their planning supersession does not close those branches.

Two specification questions must be resolved before an authoritative power run:

1. **Per-configuration denominators.** The analysis document defines
   `N = 6 * F * 3 * 10` for the entire study, then uses N for acceptance coverage,
   goodput and raw correctness. State explicitly that each configuration uses
   its own scheduled denominator `n_r = F * 3 * 10`, including its missing cells,
   while total N is only the study-wide schedule/accounting denominator. With
   a per-arm numerator and the literal global denominator, even an arm accepting
   every task has coverage 1/6; the five-percentage-point goodput power target
   changes meaning. Pin the contrast statistic and its denominator too.
2. **Synthetic paired-outcome model.** Seed 20260915, baseline goodput and
   within-family correlation do not uniquely define a simulation. Specify the
   outcome-generating distribution, family/task/repetition dependence, coupling
   between treatment/control outcomes, construction of the effect, acceptance
   and error model, and statistic used in the planned label-swap test. Review
   these before running a simulation intended to select the smallest eligible F.

No authoritative power simulation was run in this coordination update; inventing
those assumptions would silently change the proposed design. Once specified,
implementation and synthetic calibration can proceed independently of M4 repair.

The proposed range implies 90-600 distinct tasks and **5,400-36,000 scheduled
configuration/task/repetition cells**, before decomposition, verification,
additional calls or secondary studies. Review feasibility and budget before
freezing the actual manifest. If the power/resource gate fails, retain the
protocol's descriptive-only outcome instead of claiming confirmatory power.

The published command examples also depend on #90/#91 code and files that are
not present on reviewed main (for example the launch/protocol/reproduction
paths and referenced tests). Integrate and validate these dependencies before
calling the fixture-promotion and launch rules executable protections. A
documentation statement alone does not demonstrate structural enforcement.

That protocol-only update changed no other branch. Subsequent authorized triage
merged #106, closed obsolete #22, repaired #109 and added the required failing
pytest gate/corrected claims in #117. The detailed actions and concurrent owner
dispositions are recorded in [PR_TRIAGE_2026-09-15.md](PR_TRIAGE_2026-09-15.md).

## Six final gates

| Gate | Required result | Snapshot verdict / missing proof |
| --- | --- | --- |
| Core architecture | PASS on integrated RC, with independent review and enforced checks | AMBER: binding activation merged; #108 review and #117 implementation gaps remain; required approval count is 0 |
| M4 trust boundary | QUALIFIED with no skipped mandatory security capability tests | RED: capable-runner qualification outstanding; changes proposed in #108 need reviewed compatibility |
| Runtime/recovery | PASS plus completed 72h soak after clean shorter runs | RED: retained runtime failures, integration and elapsed soak evidence outstanding |
| Clean installation | PASS from genuinely blank VM on RC | AMBER: tooling and CI pass; independent blank-VM RC execution not evidenced |
| Canonical demo | PASS in real browser and guest on final deployed revision | AMBER: current browser/Pages jobs pass; full final narrative acceptance outstanding |
| ER1 | COMPLETE, reproducible and independently audited regardless of H1 outcome | RED: protocol/corpus reconciliation and confirmatory measurements outstanding |

**0/6 final release gates are fully evidenced at this snapshot.**
This is a release-gate count, not a claim that engineering progress is zero.
Earlier percentage estimates were planning judgments, not a measured
work-breakdown calculation; do not add them to this gate count.

## Retained failures and outstanding gates

| Revision / run | Observation | Required treatment |
| --- | --- | --- |
| #108 head b3b2a5a; [Factory runtime evidence 34940491451](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34940491451), job 104287844727 | Lease-revocation test errors reading observations: SQLite database locked at PRAGMA synchronous=FULL | Reproduce/classify/fix without hiding the failure through retries |
| Main eefee6a; [controller/provider run 34958593443](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34958593443), job 104346500887, Python 3.12 | forbidden-tool test expected (VIOLATED, allowed_tools), observed (VIOLATED, lease_generation); 917 tests, one failure, 21 skips | Determine why the terminal reason differs; no causal conclusion from this assertion alone |
| Main eefee6a; [Command Station run 34958593479](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34958593479), job 104346500857, Python 3.13 | CLI real-backend test expected exit 0, observed 2; 917 tests, one failure, 21 skips | Classify retained process evidence; the accompanying runpy warning alone is not a demonstrated cause |
| #108 production review | Receipt schema compatibility, bounded lease I/O/resource enforcement, reap-timeout lifecycle, concurrent diagnostic attribution, fixture timeout consistency | Repair owner supplies genuine failing regression/reversion coverage; independent reviewer accepts final changes |
| Active main protection | No mandatory approving review; new status/binding checks optional | Maintainer requires at least one independent approval and adds the two checks, preserving existing protections |

Historical main eefee6a ownership run 34958593498 and clean-install run 34958593422 passed.
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
2. Runtime/DSM owner repairs #117; coordinator integrates independently reviewed #107 and reconciles #94/#93 and benchmark ports.
3. Maintainer completes review/check enforcement; runner and corpus lanes proceed now.
4. Coordinator assembles accepted changes, freezes an RC candidate and dispatches
   the parallel qualification lanes in [QUALIFICATION_EXECUTION_PLAN.md](QUALIFICATION_EXECUTION_PLAN.md).
5. Science owner freezes ER1 and runs it after the required trust/prerequisite gates pass.

Keep each tracker update bound to source revisions, run attempts, artifacts and
review dispositions. Opening or merging a PR alone cannot turn a release gate green.
