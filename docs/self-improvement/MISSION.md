# RESIDUAL Perpetual Self-Improvement Mission

Status: bootstrap for M7 / issue #291

## Objective

RESIDUAL is a governed workload of RESIDUAL. The perpetual mission observes repository health and accepted roadmap state, creates bounded improvement candidates, executes eligible work through the existing Station control loop, retains evidence, and repeats by generation.

This mission does not create a second implementation authority. Station task state, GoalSpec, LoopController, local checks, revision-bound review, integration receipts, and export remain the execution path.

## Commands

    residual revision doctor
    residual revision doctor --json
    residual self-improve plan --candidates docs/self-improvement/candidates.json
    residual self-improve run --candidates docs/self-improvement/candidates.json --station-data .residual/self-improve

Revision Doctor is read-only. self-improve plan is read-only. self-improve run refuses a dirty source checkout or a blocking health error, validates every candidate, clones the source into a Station-managed workspace, and delegates implementation, checking, review, integration, and export to Station.

## Hierarchy

Mission Governor
- Health Director
  - Revision Doctor
- Roadmap Director
  - Scout
  - Research
- Swarm Director
  - Implementation
  - Critic
  - Verifier
  - Integrator

The hierarchy is an organization contract, not a claim that each named role already has an independent model process. Distributed workers may satisfy implementation lanes through Station's existing worker protocol.

## Authority boundary

Autonomous authority covers inspection, deterministic planning, and managed implementation for explicitly validated unprotected candidates.

The mission has no authority to merge to production. Protected trust-boundary changes require a separate governed mission and review. Bootstrap protected paths include GitHub workflows, Factory, Station internals, verifier surfaces, GoalSpec, LoopController, receipts, and the Factory ownership baseline.

A generated export is a candidate successor. It is not accepted main and is not production qualification.

## Frozen evaluator rule

A candidate may not write any external evaluator file used to certify that candidate. The Station check contract is generated before execution and is immutable for that generation. A candidate therefore cannot make itself pass by rewriting its own tests or acceptance criteria.

Changing an evaluator is a separate generation whose acceptance is provided by a different frozen evaluator.

## Candidate contract

Each ImprovementCandidate declares:
- unique id and title
- bounded instruction
- explicit writable files
- explicit read-only context
- dependencies
- immutable Station checks
- local or cloud route
- external evaluator files

Unknown fields, protected writable paths, missing evaluator files, evaluator/write overlap, malformed paths, and malformed Station specifications fail closed before model execution.

## Health Director / Revision Doctor

The bootstrap doctor records exact HEAD, main identity, branch, dirty state, roadmap snapshot identity, roadmap lag, current build-order items, and structured findings. The report is content-addressed without embedding the machine-specific repository path in its identity.

A roadmap SHA is treated as a historical status snapshot. If it is an ancestor of current main, lag is a warning to reconcile evidence; the doctor does not rewrite the SHA and does not turn later commits into an implicit PASS. A divergent snapshot is blocking.

## Perpetual generation lifecycle

Observe -> Plan -> Validate Candidate -> Managed Clone -> Implement -> Check -> Review -> Integrate -> Export -> Governed Promotion -> Observe

Failures and UNKNOWN/BLOCKED states remain evidence. A later successful generation does not erase earlier failure history.

## Recursive improvement

The same mission can propose improvements to its planning, routing, prompts, heuristics, tests, benchmarks, or implementation. The frozen-evaluator rule prevents one generation from redefining the evidence that certifies itself.

When accepted M6 Scientist primitives land on main, Scientist-originated ImprovementSpecs can feed the same candidate queue. Until then, open research PRs remain research and are not imported as production authority.

## Distributed workload

Large generations should be decomposed into non-overlapping candidate scopes. Station dependency waves and remote inference workers provide the existing distribution mechanism. A future adaptive decomposition layer may originate candidates, but it must still produce this bounded contract before implementation starts.

## Generation 0001

Generation 0001 establishes the control surface rather than claiming autonomous improvement success. It introduces Revision Doctor, hierarchical planning, bounded candidate validation, Station delegation, frozen-evaluator/protected-path gates, an initial documentation candidate, tests, and this mission contract.

The first candidate is intentionally low risk: produce an operations runbook inside the managed workspace. Its purpose is to exercise the full mission path before allowing broader writable scopes.
