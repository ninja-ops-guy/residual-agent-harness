# Reliability from Unreliable Computation
## An Evidence-First Architecture for Verifiable Multi-Agent AI Systems

**Author:** Mike Olivares  
**Status:** Working IEEE-style manuscript draft  
**Date:** 2026-09-14

> **Research hypothesis:** AI reliability does not necessarily require making individual models reliable. Reliable accepted behavior may emerge when unreliable computation is constrained, observed, independently verified, and deterministically integrated.

## Abstract

AI reliability is commonly approached as a property to be improved within the model itself. This paper investigates a complementary systems hypothesis: reliable accepted behavior can emerge from unreliable AI computation when execution is constrained, behavior is observable, outputs are independently verified, and accepted changes are integrated deterministically. We present Residual, an evidence-first execution architecture that treats model-driven workers as untrusted computational processes rather than authorities over system state. Workers operate under immutable contracts and bounded capabilities, emit observations and provenance-preserving receipts, and submit candidate results to an independent acceptance boundary. A deterministic integrator controls which verified results become accepted state. We formalize the distinction between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`, and define a controlled evaluation program centered on Accepted Error Rate (AER), Failure Containment Rate (FCR), worker-degradation curves, matched-budget baselines, and independently graded outcomes. The architecture is informed by prior work in verified cyber planning, proof-carrying plans, SAT/SMT-based checking, counterexample-guided revision, and evidence-first engineering. Current implementation evidence supports the existence and testability of the control mechanisms, but does not yet establish the central empirical hypothesis. Experimental Release 1 therefore binds preregistered study conditions, normalized observations, publication artifacts, and upstream evidence hashes so the central claim can be supported or falsified by reproducible data rather than architectural argument alone. The contribution is a falsifiable systems model of AI reliability in which generation authority is separated from acceptance authority.

**Index Terms:** AI reliability, multi-agent systems, runtime verification, deterministic integration, provenance, fault containment, formal verification, agent orchestration.

---

## I. Introduction

Large language models and model-driven agents are stochastic components whose outputs may be incorrect, inconsistent, or unsupported even when they appear plausible. A dominant response is to improve the component: use a more capable model, improve training or alignment, increase inference-time reasoning, or construct stronger prompts. These approaches are valuable, but they implicitly place much of the reliability burden on the generator itself.

Computing systems have repeatedly solved an analogous problem differently. Networks lose packets, disks fail, processes crash, distributed nodes disagree, and untrusted programs violate assumptions. Dependable systems therefore constrain authority, observe execution, validate outputs, preserve provenance, and control state transition. The central question of this paper is whether AI systems can exploit the same separation between component reliability and system reliability.

We test the hypothesis:

**H1:** System-level AI reliability can increase without increasing individual model reliability when model actions are bounded by explicit contracts, execution produces independently inspectable evidence, candidate outputs are externally verified, and accepted outputs are integrated through deterministic rules.

The corresponding null hypothesis is:

**H0:** These mechanisms do not significantly improve system-level reliability relative to unconstrained or conventionally orchestrated execution.

The key distinction is between generation and acceptance. Residual permits stochastic models to propose computation, but does not grant those models unilateral authority to define successful completion or mutate accepted state. This design treats intelligence as potentially useful but untrusted compute.

This paper makes four contributions:

1. A formal distinction between worker correctness and accepted-system correctness.
2. An evidence-first architecture for bounded heterogeneous AI execution.
3. A deterministic acceptance and integration boundary.
4. A reproducible ablation methodology and evidence pipeline for testing whether architectural controls can improve accepted reliability while model capability is held constant.

## II. Research Lineage and Design Motivation

The architecture emerged from a broader evidence-first research program rather than from agent orchestration alone. Prior Verified Cyber Planning work separated proposal from correctness: language-model or heuristic components could propose plans while SAT/SMT-style verification, frame constraints, policy checks, counterexamples, and proof artifacts established an independent correctness boundary. Later work introduced a Cyber intermediate representation, CPCF-style portable plan certificates, standalone verification, incremental replanning, temporal and policy rules, attack-path discovery, planner portfolios, digital-twin state, and reproducible benchmark records.

These implementation checkpoints are research lineage and engineering evidence, not evidence for the new system-level reliability hypothesis.

That research established a recurring pattern:

```text
uncertain generation
        ↓
candidate artifact
        ↓
observable evidence
        ↓
independent verification
        ↓
controlled acceptance
```

Residual generalizes this pattern from cyber plans to arbitrary agent work. Boundary-oriented CIC research and LDD methodology further motivate explicit treatment of interactions, failure boundaries, and learning from observable discrepancies. These prior lines are used here as architectural motivation; claims unique to Residual remain subject to the experiments defined below.

## III. Reliability Model

Let `X` denote the event that a worker-generated result is correct with respect to a task specification, and let `A` denote the event that the system accepts that result.

Raw component reliability is:

`P(X)`

The quantity of interest for an evidence-gated system is:

`P(X|A)`

By Bayes' rule:

`P(X|A) = P(A|X)P(X) / P(A)`

A useful acceptance mechanism has high sensitivity to valid work and low false acceptance:

`P(A|X) >> P(A|¬X)`

Under those conditions, `P(X|A)` may substantially exceed `P(X)` without any change to the underlying worker.

The architecture therefore does **not** claim to make an unreliable model intrinsically reliable. It attempts to reduce the probability that unreliable computation crosses the acceptance boundary.

This formulation also exposes a trade-off. A stricter verifier can increase conditional correctness while decreasing acceptance rate and throughput. Reliability must therefore be evaluated jointly with latency, monetary/token/GPU cost, coordination overhead, and rejected or `UNKNOWN` work rather than as a free improvement.

## IV. Residual Architecture

Residual implements the sequence:

```text
constrain → observe → verify → deterministically integrate → evaluate
```

A task is compiled into an execution plan and one or more immutable `WorkerContract`s. A contract binds inputs, expected outputs, permitted tools, filesystem boundaries, and resource limits before worker execution. Contract violations are terminal events and are recorded as observations rather than being handled as conversational suggestions.

Workers execute as disposable computational units in isolated work contexts. Their authority is intentionally narrower than the authority of the control plane. Outputs, tool activity, verifier outcomes, and relevant provenance flow through an evidence bus. Receipt records bind execution and verification context so later stages can reconstruct why a candidate result was accepted or rejected.

Verification is external to the worker's self-assessment. A worker may claim completion, but completion is not authoritative until required checks produce an acceptable state. `PASS`, `FAIL`, `UNKNOWN`, and `SKIPPED` are represented distinctly to avoid collapsing missing evidence into success. This fail-closed bias is important when telemetry is stale, verification is unavailable, or evidence is incomplete.

The deterministic integrator is the state-transition boundary. Parallel workers may be stochastic and heterogeneous; the rules determining eligible artifacts, ordering, conflict handling, and accepted integration are deterministic. This permits nondeterministic search outside the trusted boundary while seeking reproducible state transition inside it.

The architecture is model-agnostic. Capability routing can select local or remote engines according to capability, cost, latency, availability, and policy. This enables a further hypothesis: once acceptance is externally verified, heterogeneous lower-cost compute may be economically useful even when its individual success rate is lower, provided its failure modes are sufficiently observable and containable.

## V. Implementation Status

The current repository contains an implemented research prototype with controlled evaluation tooling, evidence handling, routing, receipt binding, worker contracts, bounded Factory execution, adaptive assurance, and deterministic integration primitives.

Experimental Release 1 adds a canonical analysis boundary on top of those execution systems. It consumes normalized, independently graded observations and computes Accepted Error Rate, Failure Containment Rate, acceptance rate, accepted correctness, raw worker correctness where observable, latency, cost, family-level results, worker-degradation curves, and baseline deltas. Study, external assurance, and Factory evidence can be translated into the normalized schema without granting the analyzer authority over execution or acceptance.

Several claims remain deliberately unsupported until live controlled experiments are complete. The manuscript does not claim arbitrary-task quality improvement, universal production readiness, distributed consensus, or guaranteed cost/latency gains.

Maintaining this distinction between implemented control and demonstrated outcome is part of the evidence-first methodology.

## VI. Experimental Methodology

The primary experiment is a controlled ablation in which the underlying model, task corpus, prompts, temperature policy, and environment are held constant while system controls are introduced progressively.

| Configuration | Constraints | Evidence / Verification | Deterministic Integration | Swarm |
| --- | --- | --- | --- | --- |
| A: Raw model | No | No | No | No |
| B: Conventional orchestration | Partial | Partial | No | Optional |
| C: Contracted | Yes | No | No | No |
| D: COV | Yes | Yes | No | Optional |
| E: COVD | Yes | Yes | Yes | Optional |
| F: Fixed swarm | Yes | Yes | Yes | Yes |
| G: Market/swarm | Yes | Yes | Yes | Adaptive |

The confirmatory experiment freezes exact model identifiers, inference settings, tool surfaces, task corpus, verifier revisions, budgets, trial counts, stopping rules, and source revision before evaluation. Results are recorded as one normalized observation per `(case, trial, configuration, degradation level)`.

Each observation records at minimum whether the result crossed the acceptance boundary and whether an independent grader judged the result correct. Where a meaningful pre-acceptance worker candidate can be independently graded, raw worker correctness is recorded separately rather than inferred from controller outcome.

### A. Fixed-model ablation

Hold model capability constant while progressively introducing contracts, evidence, independent verification, deterministic integration, and bounded swarm execution. The primary comparison is AER relative to raw/direct and conventional baselines.

### B. Model-degradation experiment

Repeat the workload with progressively less reliable workers while preserving the acceptance architecture. Degradation may be implemented through weaker models, reduced context, constrained inference budgets, or preregistered deterministic corruption, provided the mechanism is fixed before evaluation.

The desired comparison is not whether Residual makes the weaker model smarter. It is whether:

`P(correct | accepted)`

remains materially above raw worker correctness as worker quality decreases.

### C. Fault-injection experiment

Introduce controlled failures including:

- malformed outputs;
- conflicting edits;
- forbidden tool attempts;
- resource exhaustion;
- stale telemetry;
- verifier unavailability;
- worker termination;
- tampered evidence or receipts;
- changed verifier revisions;
- incomplete dependency evidence.

These tests measure whether faults are contained before accepted state rather than merely whether faults occur.

### D. Matched-budget experiment

Compare stronger direct execution with Residual using weaker or heterogeneous workers under frozen equivalent or transparently normalized budgets. Verification and orchestration cost belongs in the Residual budget. An additional control should expose an equivalent verification-compute budget to the conventional baseline without granting that baseline Residual's deterministic acceptance architecture.

## VII. Metrics and Statistical Analysis

The primary metric is **Accepted Error Rate (AER)**:

`AER = incorrect accepted outputs / all accepted outputs`

AER is undefined when no output is accepted. Such a condition is reported as `UNKNOWN`, not as zero error.

The second primary metric is **Failure Containment Rate (FCR)**:

`FCR = detected or contained faulty executions / all injected faulty executions`

Secondary measures include:

- accepted-task throughput;
- acceptance rate;
- accepted correctness;
- independent task success;
- raw worker correctness where independently measurable;
- false rejection;
- verifier rejection;
- rework;
- conflict rate;
- final test pass rate;
- elapsed time;
- normalized compute cost;
- cost per independently correct accepted result.

For binary correctness outcomes, confidence intervals and paired comparisons should be reported at the task level. Repeated runs should be treated as clustered observations rather than independent task samples. Effect sizes should accompany significance tests. Where workloads differ materially, results should be stratified by task class.

The strongest evidence for H1 would be a statistically and practically meaningful reduction in AER between configurations while the underlying model remains fixed.

A separate efficiency frontier should plot accepted correctness against cost and latency. This prevents a trivially conservative system that rejects nearly everything from being described as superior. The target is not maximum rejection; it is a favorable reliability-throughput-cost frontier.

### Evidence binding

Experimental Release 1 produces create-only publication artifacts:

- `results.json` — machine-readable metrics;
- `report.md` — human-readable results;
- `evidence-manifest.json` — hashes binding the preregistration manifest, normalized observations, result, and upstream evidence;
- `plot-data.csv` — publication plotting data;
- `figures/degradation-aer.svg` — worker-degradation/AER visualization.

Paper tables and figures should be generated from these artifacts rather than manually transcribed example values.

## VIII. Expected Results and Falsification Criteria

No empirical result is asserted in this section.

H1 is supported only if controls produce reproducible improvements in accepted-system correctness under fixed model capability. It is weakened if improvements disappear across task classes, are explained primarily by increased compute, require rejecting nearly all work, or require verifier knowledge that effectively solves the task itself.

H1 is falsified for the tested domain if COVD does not materially improve AER or failure containment relative to appropriate baselines.

A stronger economic claim additionally requires a favorable reliability/cost or reliability/latency frontier under matched accounting.

Any example benchmark numbers used in specifications or documentation must remain clearly labeled as examples until reproduced by frozen evaluation artifacts.

## IX. Threats to Validity

Verifier dependence is the principal epistemic risk. A verifier can be deterministic and still encode an incomplete or incorrect specification. Correlated failure between generator and verifier can defeat apparent independence.

Other threats include:

- benchmark leakage;
- task selection bias;
- nondeterministic external tools;
- flaky tests;
- environment drift;
- verifier overfitting;
- correlated generator/verifier errors;
- hidden-test contamination;
- workload classes where verification is nearly as difficult as generation;
- optional stopping or post-hoc trial counts;
- incomplete accounting of verifier and orchestration compute.

The study should freeze workloads, preserve raw observations, version verifiers and policies, and distinguish `UNKNOWN` from `PASS`.

External validity is also limited. Software-engineering tasks with executable tests are easier to verify than open-ended judgment tasks. Results should not be generalized to arbitrary autonomous systems without domain-specific acceptance evidence.

Deterministic integration controls state transition but does not itself provide distributed consensus or solve every failure mode of multi-node infrastructure.

## X. Discussion

The proposed model reframes the role of an AI agent. Instead of being an autonomous authority whose confidence determines success, the agent becomes a candidate-computation generator operating inside a larger reliability system.

This resembles fault-tolerant computing more than conversational delegation: components may fail, but failures need not become system truth.

This view also changes the economics of model routing. If a scheduler can estimate task-conditioned verifier-pass probability, cost, and latency for each engine, routing can optimize expected **verified utility** rather than raw model prestige.

A future scheduler might model each engine using:

- capability;
- historical verifier-pass rate;
- latency distribution;
- marginal cost;
- context capacity;
- availability;
- privacy boundary;
- failure rate;
- resource location.

Over time, observed receipts could support empirical estimates of which engines produce acceptable work for which task classes. This creates a path toward a market-like scheduler for verified intelligence, although broad superiority remains an empirical question.

The deeper claim is deliberately modest:

> **Model reliability and system reliability are not identical variables.**

A system may improve the latter through architectural controls even when the former is unchanged. Whether the magnitude of that improvement justifies its orchestration cost is an empirical question that Residual is designed to answer.

## XI. Conclusion

This paper proposes that dependable AI execution need not rely exclusively on dependable individual models. Residual separates generation authority from acceptance authority through immutable contracts, observable evidence, independent verification, provenance-preserving receipts, and deterministic integration.

The resulting hypothesis is falsifiable: with model capability held constant, these controls should reduce incorrect accepted computation and improve failure containment at measurable cost.

Current implementation evidence establishes a substantial testable system and a canonical evidence pipeline but does not yet establish the hypothesis. The next phase is therefore experimental rather than rhetorical: freeze independently authored workloads, execute ablations, degradation and fault-injection studies, publish raw evidence, and report both successful and negative results.

---

## Working References

1. L. Lamport, R. Shostak, and M. Pease, “The Byzantine Generals Problem,” *ACM Transactions on Programming Languages and Systems*, 1982.
2. G. C. Necula, “Proof-Carrying Code,” in *Proceedings of POPL*, 1997.
3. E. M. Clarke, O. Grumberg, and D. A. Peled, *Model Checking*. MIT Press, 1999.
4. C. Baier and J.-P. Katoen, *Principles of Model Checking*. MIT Press, 2008.
5. J. C. Reynolds, “Separation Logic: A Logic for Shared Mutable Data Structures,” in *Proceedings of LICS*, 2002.
6. J. Gray and A. Reuter, *Transaction Processing: Concepts and Techniques*. Morgan Kaufmann, 1992.
7. Residual project specifications and evaluation artifacts, this repository, 2026.
8. M. Olivares, “Verified Cyber Planning,” working manuscript and accompanying research artifacts, 2026. Bibliographic metadata to be finalized.
9. Additional related work already tracked in [`../research.md`](../research.md), including FrugalGPT, RouteLLM, ReWOO, LLMLingua-2, CEGIS, and heterogeneous-agent research.

## Appendix A — Experiment Completion Checklist

- [ ] Freeze benchmark/task corpus and publish its hash.
- [ ] Freeze model versions, inference settings, prompts, tool versions, verifier revisions, and policies.
- [ ] Run every preregistered configuration and preserve complete observation logs and receipts.
- [ ] Label ground truth independently of worker self-reports.
- [ ] Compute AER, FCR, acceptance rate, accepted correctness, throughput, cost, rework, conflicts, rejection, and final test pass rate.
- [ ] Run model-degradation and fault-injection studies.
- [ ] Run matched-budget comparisons with verifier/orchestration cost included.
- [ ] Perform clustered/paired statistical analysis with confidence intervals and effect sizes.
- [ ] Publish negative results and `UNKNOWN` outcomes.
- [ ] Replace working citations with verified IEEE bibliographic entries.
- [ ] Release reproducibility instructions and artifact hashes.

## Repository Research Links

- [Research claim and prior art](../research.md)
- [Controlled evaluation protocol](../controlled-evaluation.md)
- [Experimental Release 1](../reliability-experimental-release.md)
- [Evaluation documentation](../evaluation.md)
- [Architecture](../architecture.md)
