# RESIDUAL-ABLATION-001 — Measured R0–R5 Reliability Ablation

**Status:** APPARATUS IMPLEMENTATION / CONFIRMATORY EXECUTION PENDING  
**Protocol:** `RESIDUAL-ABLATION-001`  
**Architecture inventory baseline:** `91d32fd8b713c68c1cd2e473013c9e1c33b93572`

## Research question

Does progressively externalizing orchestration, authority boundaries, observation,
verification, and deterministic integration improve accepted-system reliability
while worker/model capability is held constant?

The experiment does **not** test whether RESIDUAL makes the underlying model
intrinsically smarter. It tests whether the control architecture changes which
candidate computations become accepted system state.

## Canonical arms

The measured campaign reuses the frozen cumulative R0–R5 definitions in
`residual.eval_frozen.configs`: R0 raw execution; R1 orchestration; R2
contracts; R3 constraints + observation + verification; R4 deterministic
integration; R5 dynamic swarm orchestration.

Arm definitions are hash-bound in every `ExecutionManifest`. A measured run
must execute all six arms in canonical order for every `(task, repeat)` block.

## Held constants

For one confirmatory campaign, these must remain identical across all arms:
provider, model ID/version, prompt policy, inference settings, tool environment,
grader ID/version, execution environment, budget policy, task corpus, and
workload hash. Changing one creates a new campaign and must not be mixed into
the same confirmatory aggregate.

## Endpoints

Primary endpoint:

`ASSR = P(X ∧ A)`

where X is independent correctness and A is acceptance. ASSR is unconditional,
so rejecting nearly everything cannot manufacture a good primary result.

Safety endpoint:

`UAR = P(A ∧ ¬X)`

Also report conditional false-acceptance `P(¬X | A)` alongside acceptance
coverage. Secondary metrics are raw correctness, incorrect suppression, false
rejection, fault capture, latency, token/cost totals, rework, conflicts,
operator interventions, recovery, duplicate work, and unauthorized actions.

## Pairing and stopping

The paired block is `(task_id, repeat)`; every block contains R0–R5 exactly
once. Minimum repeats are **3**. There is no outcome-dependent early stopping.

Confirmatory comparisons are R4 vs R0 (COVD effect) and R5 vs R4 (incremental
dynamic-swarm effect). R1–R3 are mechanism-attribution arms. Freeze statistical
analysis code and uncertainty/multiplicity rules before confirmatory outcome
access.

## Missingness

`UNKNOWN`, aborted, provider-failed, and incomplete runs remain in every
unconditional denominator. Conditional metrics are `null` when their
mathematical denominator is zero. Negative or UNKNOWN cells are retained rather
than replaced by a favorable rerun.

## Evidence contract

`residual.eval.ablation001` is measured-only. The adapter cannot supply
task/config/repeat identity; the outer runner binds those fields. Every
observation requires at least one retained immutable evidence reference.

Each bundle binds the protocol hash, workload hash, exact source commit, held
factor hashes, canonical R0–R5 hashes, paired raw observations, aggregate
metrics, and a content-addressed bundle hash.

The measured lane is `evidence_level="measured_live"`. The existing scripted
`residual.eval_frozen` fixture remains development evidence and cannot be
relabelled as empirical evidence.

## Contamination guard

During confirmatory execution:

- do not read or modify sealed AX/SLM experimental outcomes;
- do not tune workload, verifier, thresholds, endpoints, or stopping rules
  after outcome access;
- do not replace negative/UNKNOWN cells with reruns;
- do not mix exploratory, fixture, or different-revision evidence into the
  confirmatory aggregate.

AX-21 can later become an **observational** corpus and a source of pre-frozen
stress cases, but it remains analytically separate from this confirmatory lane.

## Execution gate

Before paper-facing collection, freeze and retain: exact source commit/tree;
confirmatory FrozenWorkload; all provider/model/prompt/inference/tool/environment
and budget identities; grader/verifier revision; clean-install and ownership
qualification where the protected Factory path is used; exact workload→Factory
mapping; fresh run-identity chain; authenticated scheduler/topology evidence;
M3 receipts; isolated M4 acceptance receipts; and frozen analysis code.

Use `residual.eval_frozen.acceptance_binding` when a measured arm crosses the
protected Factory/M4 acceptance boundary.

## Falsification discipline

The experiment remains useful if RESIDUAL loses. The architecture hypothesis is
weakened for the tested domain if R4 does not produce a practically meaningful
reliability improvement over R0 at fixed model capability, or if an apparent
gain is explained primarily by extra model compute, verifier leakage, or
trivial rejection. Latency, cost, false rejection, operator burden, failures,
and null results remain first-class evidence.

## Non-claims

Landing this apparatus, passing its unit tests, or reproducing the deterministic
fixture does **not** establish that RESIDUAL improves live AI systems. That
requires a fresh measured campaign through the frozen execution gate above.
