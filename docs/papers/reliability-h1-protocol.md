# H1 Evaluation Protocol — Reliability from Unreliable Computation

**Status:** preregistration-style protocol draft.  
**Hypothesis:** system-level accepted reliability can improve without improving the underlying model when computation is constrained, observed, independently verified, and deterministically integrated.

## 1. Experimental invariant

Within each paired comparison, hold constant:

- task input and hidden grader;
- model/provider identity;
- sampling configuration and tool availability;
- prompt/task contract content except for the control mechanism under ablation;
- environment/image and dependency versions;
- verifier revision where the verifier is enabled;
- hardware class where practical;
- random schedule seed.

Do not compare a weaker raw model to a stronger Residual model and attribute the difference to architecture.

## 2. Configurations

### R0 — Raw

Single model receives the task and may return a final candidate. No Residual acceptance gate. Independent grader determines correctness after completion.

### R1 — Orchestrated baseline

Same worker model with ordinary task/tool orchestration and completion based on worker/controller success, but without receipt-bound independent acceptance semantics.

### R2 — Constrained

Add immutable execution/resource/tool/filesystem contract enforcement. Do not add semantic verification beyond the independent post-run grader.

### R3 — Constrained + Observed + Verified (COV)

Add observation/evidence capture, versioned verifier execution, PASS/FAIL/UNKNOWN/SKIPPED semantics, and receipt binding. Integration remains intentionally simplified for the ablation.

### R4 — COV + Deterministic Integration (COVD)

Candidate work can affect accepted state only through deterministic eligibility, conflict, dependency, and integration rules.

### R5 — Dynamic heterogeneous swarm

Same acceptance boundary as R4; task decomposition/routing and worker count may vary. Used to evaluate throughput and cost, not required to establish the core H1 claim.

## 3. Workload

Use at least three verification regimes:

1. **Executable software tasks:** independently authored hidden tests.
2. **Bounded planning/state-transition tasks:** independent simulator/model checker.
3. **Structured analysis tasks:** independently prepared expected structures/constraints.

Entire task families must be held out from policy/tuning decisions. Public development fixtures are never labeled confirmatory.

For every task record:

- family and difficulty;
- ground-truth/grader provenance;
- verifier type and revision;
- whether checking is materially cheaper/easier than generation;
- task size/granularity;
- sensitive/private evidence class if relevant.

## 4. Primary endpoints

### Accepted Error Rate

`AER = incorrect accepted outputs / accepted outputs`

Report an undefined AER if no output is accepted; do not convert abstention into perfect reliability.

### False Acceptance Rate

`FAR = controller-accepted but independently incorrect / controller-accepted`

### Failure Containment Rate

For fault-injection trials:

`FCR = known injected faults prevented from producing incorrect accepted state / known injected faults`

### Independent Success Rate

`ISR = independently correct completed tasks / all scheduled tasks`

This denominator includes failed, skipped, missing, and not-run trials unless a preregistered infrastructure exclusion applies.

## 5. Secondary endpoints

- acceptance and abstention/UNKNOWN rate;
- false rejection where independently correct candidates are available for analysis;
- elapsed latency: median and p95;
- accepted tasks/hour;
- provider input/output/cache/reasoning usage where exposed;
- modeled provider cost and local occupancy cost;
- cost per independent success;
- verifier runtime;
- scheduling/integration overhead;
- rework/retry count;
- conflict rate;
- tool/contract violations;
- evidence-pull bytes and remote disclosure;
- cache hit/rejection/tamper events.

## 6. Repeats and statistics

Minimum: 3 paired repeats per task/configuration. Prefer 10+ for stochastic live-model studies if budget allows.

Pair trials by task ID, model pair, and repeat index. Randomize configuration order within a paired block.

For binary outcomes:

- report raw counts and Wilson or bootstrap confidence intervals;
- use paired methods where applicable;
- bootstrap at the **task-family** level for cross-family summaries so repeated trials do not masquerade as independent families;
- report absolute risk difference for AER/FAR and ISR;
- never infer equivalence from a nonsignificant difference.

For cost/latency:

- report medians, p95, and distributions;
- include failed trials in cost totals;
- report unknown cost separately when usage/pricing coverage is incomplete.

## 7. Fault-injection matrix

Each fault must have a known injection point and expected containment layer.

| Fault | Expected layer |
| --- | --- |
| malformed worker result | schema/contract boundary |
| forbidden tool invocation | WorkerContract/runtime |
| forbidden file write | OS/runtime isolation |
| resource exhaustion | runtime budget |
| stale/missing telemetry | verifier → UNKNOWN/fail closed |
| incorrect candidate satisfying superficial format | semantic verifier / independent grader |
| tampered receipt/value | receipt integrity |
| verifier revision change | cache/receipt invalidation |
| missing prerequisite receipt | dependency validation |
| cyclic receipt dependency | receipt graph validation |
| conflicting parallel edits | deterministic integrator |
| worker crash/termination | lifecycle + scheduler |

Report both whether the mechanism detected the event and whether incorrect state actually crossed the acceptance boundary.

## 8. Model-degradation experiment

Select at least three worker-quality tiers or deliberately degrade a fixed model using preregistered context/tool restrictions. The acceptance architecture is held constant.

For each tier estimate:

- raw correctness `P(X)`;
- accepted correctness `P(X|A)`;
- coverage `P(A)`.

The central prediction is not that `P(X)` rises. It is that a useful acceptance boundary preserves a gap where `P(X|A) > P(X)` while retaining nontrivial coverage.

Plot reliability-coverage curves rather than reporting accepted accuracy alone.

## 9. Orchestration-tax experiment

Use multiple task granularities. For each task estimate:

`tax = planning + scheduling + context packaging + verification + integration overhead`

Compare the tax against saved generation cost/latency and gained parallelism. The dynamic controller is successful only when net verified utility improves. Small tasks for which tax dominates should remain single-worker.

## 10. Verifier-quality experiment

For each verifier record a quality profile against independently labeled outcomes:

- precision;
- recall;
- coverage;
- calibration where a score exists;
- revision and implementation hash.

Safety-critical claims should not rely on a verifier whose measured precision is below the project's preregistered threshold. For high-stakes checks, compare independent verifier implementations and report correlated failure.

## 11. Confirmatory stopping rule

Do not tune thresholds, prompts, router policy, verifier logic, or task contracts on confirmatory families after the first confirmatory run has been inspected. Changes require a new protocol/version and new held-out families.

## 12. H1 support and falsification

H1 is supported for a tested domain if, with model capability fixed, R4 materially lowers incorrect accepted state (AER/FAR) relative to R0/R1 while retaining useful ISR/coverage, and the benefit remains after cost/latency overhead is reported.

H1 is weakened or falsified for that domain if:

- AER/FAR does not improve materially;
- apparent reliability comes only from rejecting nearly all work;
- independent success falls enough to erase practical benefit;
- verifier cost approximates or exceeds simply solving the task with the stronger baseline;
- improvements vanish on held-out families;
- the result depends on changing model capability rather than architecture.

## 13. Artifact requirements

A publishable run must retain:

- protocol version and git commit;
- frozen lock/config/task hashes;
- model/provider identifiers and exposed sampling settings;
- verifier revisions;
- raw lifecycle/call/run logs;
- all independent grades;
- receipt/evidence artifacts needed for audit;
- analysis script version;
- generated result tables and figures;
- a manifest of missing/unknown fields.

The report must be regenerable from retained artifacts without rerunning model side effects.
