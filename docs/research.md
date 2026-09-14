# Research claim and prior art

Date: 2026-09-13. Status: implemented research prototype; novelty hypothesis.

## Working paper

The broader systems hypothesis is developed in the IEEE-style working manuscript:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The paper tests the hypothesis that system-level AI reliability can improve without increasing individual model reliability when model actions are constrained, execution is observable, outputs are independently verified, and accepted results are integrated deterministically. The manuscript intentionally separates implemented mechanisms from empirical claims and defines controlled ablations, model-degradation studies, and fault-injection experiments to test the hypothesis.

## Proposed contribution

**Counterexample-directed residual delegation with evidence negotiation:** compile
a checked workflow's unaccepted frontier into a small, independently verifiable
request for a stronger model. Preserve accepted independent work, disclose exact
source intervals on demand, and carry content-bound dependency receipts across
model boundaries and cache reuse.

The potentially useful contribution is the end-to-end contract between verifier,
frontier scheduler, evidence packet compiler, and interchangeable model providers.
The compiler chooses the unit of escalation and its evidence boundary together.
The claim is not that local/cloud mixtures, fallback routing, checkers, DAGs,
content-addressed caching, or evidence retrieval are individually new.

This repository does not establish a first-in-literature result. The bounded
prior-art review below is enough to avoid claiming ordinary routing as novel; it
does not exhaust adjacent work in verified agents, incremental computation,
program synthesis, selective prediction, and distributed query planning.

## Relevant prior art

| Work | Existing idea | Boundary of this prototype's claim |
| --- | --- | --- |
| [FrugalGPT](https://arxiv.org/abs/2305.05176) | Cost-aware model cascades | A checker-defined residual frontier and scoped evidence protocol are the proposed extra unit of control |
| [RouteLLM](https://arxiv.org/abs/2406.18665) | Learned selection between stronger and weaker models | This implementation does not learn a query router; acceptance and escalation follow explicit task checks |
| [ReWOO](https://arxiv.org/abs/2305.18323) | Separating reasoning from tool observations to reduce repeated context | Local execution and cheap tools are established ideas; this prototype tracks which obligations remain unproved |
| [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153) | Heterogeneous agents and specialized smaller models | Local/expert heterogeneity is a motivation, not a novelty claim |
| [LLMLingua-2](https://arxiv.org/abs/2403.12968) | Learned extractive prompt compression | This prototype uses exact evidence intervals, explicit omissions, and pull requests; it does not train a compressor |
| [Counterexample-Guided Inductive Synthesis](https://people.csail.mit.edu/asolar/SynthesisCourse/Lecture17.htm) | Candidate generation with counterexample feedback | Verifier-guided repair predates LLMs; the new hypothesis concerns where to transfer a residual across model boundaries |
| [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) | Filtering data and running tool workflows outside the model context | Deterministic offloading is established; this prototype adds per-obligation acceptance and receipt-bound dependencies |

The links describe primary research or the original implementer's engineering
work. Comparative statements about RESIDUAL are our interpretation, not claims
made by those authors. No third-party benchmark percentage is adopted as our own.

## Questions the prototype makes testable

1. At matched declared-task success, does residual delegation reduce reported
   remote tokens and cost per successful task relative to a full-context cascade?
2. Does explicit evidence pull preserve success under missing-context stress
   better than a fixed compact prompt?
3. Does the adaptive packet compiler reduce small-task overhead without
   increasing failures or remote disclosure?
4. Do frozen, independently checked results reduce regressions caused by an
   expert rewriting already-correct parts of a task?
5. Can receipt-bound cache reuse transfer across provider pairs while rejecting
   changed evidence, tampered values, and modified check revisions?

## Current evidence

The tests exercise partial local success, narrowly scoped cloud repair, private
dependency propagation, forbidden evidence requests, malformed responses,
call-budget exhaustion, cache tampering, changed evidence, adapter request
contracts, result/trace binding, and generated dependency graphs. A planning
example verifies proposed state transitions without searching for a solution.

The incident benchmark uses scripted workers with deliberately different
capabilities. The local fixture guesses one cause; the expert fixture reads
the decisive probe only when present in its packet. Their behavior is fully
specified in source. The host diagnosis verifier can itself compute the answer;
a bespoke local solver could therefore eliminate inference on this toy workload.
The experiment isolates controller behavior and **cannot demonstrate that cloud
reasoning is necessary or that a real model preserves quality**.

The fixed-window baseline revealed increased transfer overhead on small inputs.
The adaptive policy was designed after observing that result. Its reported
improvement is development-set evidence, not a held-out confirmatory result.

## Next experiment before a stronger novelty claim

The [controlled study runner](controlled-evaluation.md) now implements protocol
freezing, independent final grading, family-separated suites, repeated paired
trials, ablations, durable call accounting, and partial-result reporting. Its
bundled contract-stress suite is public development material. External task
authorship, live model comparisons and a matched external baseline are still
required; implementing the runner does not establish the hypothesis below.

Freeze this implementation and a provider-independent task suite with domains
where checking a candidate is substantially easier than generating one. Include
code-repair tasks graded by hidden tests, bounded planning tasks graded by
transition simulation, and structured analysis tasks graded against independently
prepared answers. Keep gold outputs and hidden tests outside model packets.

Use several local/expert pairs and repeat stochastic runs with paired task seeds.
Hold out entire task families when choosing seed sizes and the packet threshold.
Record actual input, output, cached-input and billed reasoning counts when exposed,
latency distributions, failures, abstentions, local compute time, and retrieval
misses. Expose unsuccessful runs in every denominator. Cache-disabled comparisons
isolate routing; a separate warm-cache experiment measures reuse.

Compare `full_cloud`, `cascade`, `residual_fixed`, `residual`, and `no_pull`, plus
a strong existing routing implementation using the same available tools and
budget. Our `cascade` is a transparent baseline, not a reimplementation of
RouteLLM or FrugalGPT. Evaluate authoring effort: hand-written obligations and
verifiers are part of the system's cost.

The falsifying outcome is straightforward: if matched-quality performance does
not improve cost or latency after protocol overhead and local execution costs,
the proposed architecture does not provide the intended efficiency benefit.

## What is deliberately not claimed

No new foundation model, tokenization method, neural split-inference technique,
universal verifier, learned scheduler, model-training result, provably optimal
context selector, or production readiness. The proof-like receipts certify
host checks under their stated inputs; they do not certify arbitrary truth.
