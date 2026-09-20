# RESIDUAL Mathematical Research Bench (MRB-R0)

**Status:** DESIGN-FROZEN / EXECUTION-DEFERRED  
**Activation target:** After RESIDUAL has matured beyond v1 convergence and can provide a stable, qualified experimental substrate.  
**Priority rule:** MRB MUST NOT compete with v1 convergence, production qualification, security, governance, or reliability work.

## 1. Research question

Does evidence-governed orchestration increase the depth, correctness, persistence, and cost-efficiency of mathematical reasoning achievable by a fixed model and compute budget?

MRB tests an architectural hypothesis. It does not claim that RESIDUAL can solve a Millennium Prize Problem. Frontier open problems are a later shadow-research tier that may be activated only after controlled experiments establish credible evidence.

## 2. Provenance and CIC relationship

MRB builds on the existing CIC integration contract in `docs/cic-integration.md` and its pinned research provenance (`cic-p-vs-np-research` at `005c7ad4`). The existing CIC rules remain authoritative:

- structural width is a graph property / upper-bound certificate, not a hardness oracle;
- SAT/UNSAT/UNKNOWN claims are relative to the declared bounded formal model;
- grouping and atomic acceptance are distinct from min-fill/CIC preflight;
- candidate generation and candidate acceptance remain separate;
- CIC superiority must be demonstrated by controlled ablation, not assumed.

For MRB, CIC mechanisms become experimental treatments: interaction graphs, deterministic elimination ordering, bounded feasibility/constraint propagation, structural grouping, pivotal-variable/lemma analysis, and eventually calibrated portfolio routing.

## 3. Experimental ladder

| ID | Experiment | Primary question |
|---|---|---|
| MRB-00 | Benchmark Freeze | Can we construct a reproducible, contamination-aware mathematical benchmark and preregistration? |
| MRB-01 | Single Model | What can the underlying model accomplish alone under the fixed budget? |
| MRB-02 | Generic Agent Loop | How much improvement comes from ordinary iterative tool use? |
| MRB-03 | Generic Swarm | How much improvement comes from parallelism/role specialization alone? |
| MRB-04 | RESIDUAL Core | Does governed decomposition, evidence, receipts, and integration improve verified results? |
| MRB-05 | Epistemic Memory | Does retained failure/claim history reduce rediscovery and increase useful research depth? |
| MRB-06 | Formal Verification | What changes when a proof assistant is an independent acceptance authority? |
| MRB-07 | CIC Structural Layer | Does CIC-guided grouping/decomposition/routing improve RESIDUAL under matched budgets? |
| MRB-08 | Long Horizon | Can verified research progress accumulate across long runs, resets, and worker turnover? |
| MRB-09 | Frontier Shadow | Can the qualified system generate useful, auditable partial results on genuinely unsolved mathematics? |

MRB-09 is blocked until MRB-00 through MRB-08 have completed their preregistered qualification gates.

## 4. Mathematical object model

Every material research object receives a stable identifier and typed record:

- `MRB-PROBLEM`
- `MRB-DEFINITION`
- `MRB-ASSUMPTION`
- `MRB-CONJECTURE`
- `MRB-LEMMA`
- `MRB-PROOF`
- `MRB-COUNTEREXAMPLE`
- `MRB-COMPUTATION`
- `MRB-DEPENDENCY`
- `MRB-FAILURE`
- `MRB-OPEN-QUESTION`

Minimum epistemic states:

`PROPOSED -> CONSISTENCY_CHECKED -> EMPIRICALLY_SUPPORTED -> PROOF_CANDIDATE -> FORMALIZED -> MACHINE_VERIFIED`

Orthogonal terminal/exception states:

`REFUTED`, `UNKNOWN`, `BLOCKED`, `SUPERSEDED`.

A model or worker MUST NOT self-promote a result to `MACHINE_VERIFIED`. Promotion requires an external verifier receipt bound to the exact formal statement, proof artifact, tool/version identity, and relevant dependencies.

## 5. Dual acceptance requirement

Formal compilation is necessary but not sufficient. MRB tracks two independent properties:

1. **Formal validity:** the proof assistant accepts the exact formal theorem/proof.
2. **Semantic fidelity:** the formal theorem faithfully represents the intended mathematical claim and assumptions.

Semantic-fidelity review must be independently challengeable. Vacuous formalizations, accidentally weakened statements, hidden assumptions, unsafe axioms, or specification drift are qualification failures even if the proof assistant accepts the artifact.

## 6. Research graph

MRB maintains a machine-readable dependency graph connecting problems, definitions, assumptions, conjectures, lemmas, proofs, computations, counterexamples, failures, and evidence.

The graph exists to support:

- explicit proof dependencies;
- branch termination after refutation;
- reuse of negative results;
- duplicate-work detection;
- challengeability and provenance;
- CIC structural analysis;
- scheduler decisions;
- reconstruction of why a claim was accepted.

Failed proof attempts are retained as research evidence rather than discarded when they establish a reusable counterexample, invalid assumption, failed dependency, or bounded negative result.

## 7. MRB-07 CIC ablation

Use four matched arms:

- **A — RESIDUAL:** normal qualified scheduler.
- **B — RESIDUAL + simple graph heuristics:** degree, connected components, dependency depth, or similarly inexpensive baselines.
- **C — RESIDUAL + CIC:** declared interaction graph, deterministic elimination ordering, structural width certificate, bounded constraint propagation/preflight, structural grouping, and qualified portfolio routing when available.
- **D — RESIDUAL + randomized routing:** control for exploration/order effects.

All arms MUST use matched model access, task corpus, token/call budgets, wall-clock policy, verifier authority, and evaluation protocol. Treatment-specific overhead is measured rather than hidden.

Primary measurements should include:

- verified theorem/problem completion;
- independently verified useful lemmas;
- false claims crossing each epistemic boundary;
- counterexamples found;
- duplicated work;
- dead branches terminated before expensive exploration;
- formalization success/failure;
- verifier rejection rate;
- retries/repeated dispatch;
- tokens/calls/compute cost;
- wall time;
- operator active time/interventions;
- verified useful progress per dollar;
- verified useful progress per operator-active minute;
- retained progress across context/session/worker resets.

Do not attribute an improvement to CIC when the effect can be explained by stronger grouping/atomic acceptance alone. Structural/grouping baselines are mandatory.

## 8. Benchmark and contamination controls

MRB-00 freezes methodology before model-facing runs. Benchmark selection itself should occur near activation because the model/theorem-proving landscape will change.

The activated benchmark should contain multiple tiers:

- elementary but composition-sensitive proofs;
- known historical problems with solutions hidden from the experimental workers;
- formalization tasks;
- counterexample/refutation tasks;
- deliberately malformed or subtly weakened statements;
- long dependency-chain problems;
- adversarial semantic-fidelity cases.

Where feasible, evaluation artifacts and solutions should be inaccessible to research workers and exposed only to independent graders/verifiers. Known-solution reconstruction must be clearly separated from genuinely novel research.

## 9. Roles

Candidate roles for qualified experiments:

- conjecture generator;
- decomposition planner;
- constructive proof worker;
- counterexample/red-team worker;
- computational experiment worker;
- literature/provenance worker;
- formalization worker;
- proof-assistant worker;
- semantic-fidelity reviewer;
- epistemic auditor;
- integrator/scheduler.

Roles do not grant acceptance authority. Independent verification and Station policy determine accepted state.

## 10. Activation gates

Before MRB-00 execution, require at minimum:

- stable RESIDUAL release and reproducible installation;
- qualified long-running Station execution;
- durable epistemic state and receipts;
- deterministic/replayable experiment manifests;
- worker isolation and explicit authority boundaries;
- stable budget accounting;
- reliable failure recovery;
- independent verifier integration;
- version-pinned model/provider/tool identities;
- reproducible artifact export;
- no unresolved P0/P1 defect that could invalidate experimental evidence.

Activation requires a new review against the then-current literature, theorem-proving systems, formal tools, models, and benchmark contamination risks. Do not freeze model names or benchmark versions in R0.

## 11. Frontier and Millennium boundary

Millennium Prize problems are not benchmark items for MRB-00 through MRB-08.

After MRB-08, a frontier shadow program may investigate open problems if the preceding experiments demonstrate credible gains in verified mathematical research. Such work must distinguish:

- speculative ideas;
- computational evidence;
- partial lemmas;
- conditional results;
- formalized results;
- independently machine-verified results;
- external mathematical review.

No system-generated claim of resolving a major open problem should be promoted from internal evidence alone.

## 12. Dormancy contract

This document is intentionally being committed before execution so the core hypotheses and controls predate the results.

While status is `DESIGN-FROZEN / EXECUTION-DEFERRED`:

- no substantial compute should be allocated to MRB;
- MRB should not create release blockers;
- benchmark/model selections remain intentionally open;
- changes to hypotheses, metrics, or acceptance rules must be versioned;
- activation should create a new preregistration revision rather than silently rewriting R0.

The intended activation window is after RESIDUAL has had sufficient time to mature. The exact date is evidence-driven, not calendar-driven.

## 13. Proposed future repository layout

```text
docs/research/mathematical-research-bench/
  MRB-R0.md
  hypotheses/
    H01-orchestration.md
    H02-memory.md
    H03-cic-structure.md
    H04-formal-verification.md
    H05-long-horizon.md
  experiments/
    MRB-00/ ... MRB-09/
  schemas/
    mathematical-claim.schema.json
    proof-receipt.schema.json
    research-graph.schema.json
  benchmarks/
  cic/
  formal/lean/
  preregistration/
```

R0 records the program contract only. The expanded tree should be created when the program is activated or when doing so no longer distracts from release convergence.
