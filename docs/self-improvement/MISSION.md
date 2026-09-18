# RESIDUAL Perpetual Self-Improvement Mission

Status: bootstrap for M7 / issue #291

## Objective

RESIDUAL is a governed workload of RESIDUAL. The perpetual mission observes repository health and accepted roadmap state, creates bounded improvement candidates, executes eligible work through the existing Station control loop, retains evidence, and repeats by generation.

This mission does not create a second implementation authority. Station task state, GoalSpec, LoopController, local checks, revision-bound review, integration receipts, and export remain the execution path.

## Commands

    residual revision doctor
    residual revision doctor --json
    residual revision doctor --improve --station-data .residual/self-improve
    residual revision doctor --improve --generations 3 --station-data .residual/self-improve
    residual self-improve plan --candidates docs/self-improvement/candidates.json
    residual self-improve originate --station-data .residual/self-improve
    residual self-improve run --candidates docs/self-improvement/candidates.json --station-data .residual/self-improve
    residual self-improve cycle --station-data .residual/self-improve
    residual self-improve lineage --generations 3 --station-data .residual/self-improve

Revision Doctor and self-improve plan are read-only unless the operator explicitly supplies --improve. That flag enters the same governed lineage runtime rather than adding a separate repair authority. originate creates a Station-managed planning project with two independent scouts (health and roadmap) and a dependent composer. The composer has proposal authority only: its candidate manifest is retained as an artifact and must pass the deterministic Mission Governor before it can execute. Without --allow-command-checks, origination is constrained to non-executable documentation/data improvements; code proposals are rejected before execution. With that explicit permission, code candidates may use only governor-derived frozen-evaluator checks. run executes an explicit validated candidate manifest. cycle chains one origination and execution only when source HEAD, source-report identity and mission-plan identity are unchanged between the two stages. lineage repeats that cycle for a bounded 1-10 generations.

All execution occurs in Station-managed clones. Every managed clone must prove that its HEAD is exactly the doctor-certified source HEAD before a worker runs.

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

The hierarchy is partly executable in the bootstrap: Health Scout and Roadmap Scout are independent Station tasks and the Composer depends on both, creating an explicit two-lane scout wave followed by synthesis. The implementation candidate DAG is then a separate Station project. Station's worker protocol remains the distribution surface; the bootstrap CLI itself does not claim that batch is a globally parallel scheduler.

## Authority boundary

Autonomous authority covers inspection, evidence-bound origination, deterministic candidate admission, and managed implementation for explicitly validated unprotected candidates.

The mission has no authority to merge to production. Protected trust-boundary changes require a separate governed mission and review. Bootstrap protected paths include GitHub workflows, Factory, Station internals, verifier surfaces, GoalSpec, LoopController, receipts, frozen evaluation, swarm/evidence/scheduler/integrator surfaces, the Factory ownership baseline and every file pinned by that baseline. M7 also freezes its mission policy, current-status/roadmap authority inputs, safety regression, and historical generation records against autonomous writes.

A generated export is a candidate successor. It is not accepted main and is not production qualification.

## Frozen evaluator rule

A candidate may not write any external evaluator file used to certify that candidate, and no other candidate in the same generation may write it either. Candidate writable scopes may not overlap. If one candidate reads another candidate's generated file, it must declare that writer as a dependency.

Executable-code candidates require existing frozen Python evaluators under tests/test_*.py. ImprovementCandidates are not permitted to author executable command checks at all. After deterministic admission, the Mission Governor derives the pytest command for each declared evaluator and inserts it into the immutable Station check contract. The evaluator starts Python in isolated mode, disables third-party pytest plugin autoload before importing pytest, and only then exposes the candidate repository to the test process. This removes model-authored argv and repository-level pytest bootstrap shadowing from the recursive control path.

Test-runner and import-control surfaces such as pytest configuration, conftest.py, tests/__init__.py, sitecustomize.py, usercustomize.py, and the mission's own safety regression are protected from autonomous writes. Changing a frozen evaluator or evaluator-control surface requires a separate externally governed mission rather than the generation it certifies.

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

The bootstrap doctor records exact HEAD, known main identity, whether the source contains that main revision, branch, dirty state, roadmap and current-status snapshot identities, snapshot lag, current build-order items, and structured findings. The report binds the raw roadmap, current-status, M7 mission policy, M7 controller, M7 safety regression, and Factory ownership-manifest bytes while excluding the machine-specific repository path from its identity. A source that is behind or diverged from known main is blocking.

A roadmap SHA is treated as a historical status snapshot. If it is an ancestor of current main, lag is a warning to reconcile evidence; the doctor does not rewrite the SHA and does not turn later commits into an implicit PASS. A divergent snapshot is blocking.

## Perpetual generation lifecycle

Observe -> Plan -> Scout Health + Scout Roadmap -> Compose Proposal -> Deterministic Admission -> Managed Clone -> Implement -> Check -> Review -> Integrate -> Export -> Governed Promotion -> Observe

Failures and UNKNOWN/BLOCKED states remain evidence. A later successful generation does not erase earlier failure history.

## Recursive improvement

The same mission can propose improvements to its planning, routing, prompts, heuristics, tests, benchmarks, or implementation. The frozen-evaluator rule prevents one generation from redefining the evidence that certifies itself.

Experimental lineage mode turns an accepted Station successor into the source repository for the next generation, entirely inside the Station data area. The original checkout is not rewritten. The M7 governor module loaded by the initiating process remains frozen for the whole lineage even if a candidate edits residual/self_improvement.py; that edited controller cannot grant itself more authority during the lineage that created it. Each generation must produce a different Git tree or successor export is withheld. A lineage stops on incomplete origination, failed/incomplete execution, no-op output, or the configured generation bound.

When accepted M6 Scientist primitives land on main, Scientist-originated ImprovementSpecs can feed the same candidate queue. Until then, open research PRs remain research and are not imported as production authority.

## Distributed workload

Large generations should be decomposed into non-overlapping candidate scopes. Station dependency waves and remote inference workers provide the existing distribution mechanism. A future adaptive decomposition layer may originate candidates, but it must still produce this bounded contract before implementation starts.

## Generation 0001

Generation 0001 establishes the control surface rather than claiming autonomous improvement success. It introduces Revision Doctor, a real two-scout-plus-composer origination DAG, bounded generation-wide candidate validation, exact-source Station delegation, canonical ownership protection, constrained frozen-evaluator commands, an initial documentation candidate, tests, and this mission contract.

The first candidate is intentionally low risk: produce an operations runbook inside the managed workspace. Its purpose is to exercise the full mission path before allowing broader writable scopes.
