# EXP-M6-SLM / SLM-00 — Corpus and Benchmark Freeze

Status: PREREGISTRATION DRAFT — no StationLM training may begin until this protocol is frozen.
Date: 2026-09-20

## Research question
How does progressively externalizing agent cognition into deterministic control infrastructure change the minimum model capacity required to achieve a fixed level of verified autonomous task performance?

Novelty is not assumed. A literature/prior-art matrix MUST be completed before publication claims are made.

## Program
SLM-00 corpus/benchmark freeze; SLM-01 baselines; SLM-02 Residual-Nano (30–80M); SLM-03 StationLM (150–400M); SLM-04 tokenizer ablation; SLM-05 harness ablation; SLM-06 routing economics; SLM-07 adversarial qualification; SLM-08 AX-21 shadow deployment; SLM-09 candidate qualification.

## SLM-00 freeze gate
Before model results are inspected, freeze:
1. task taxonomy and inclusion/exclusion rules;
2. observation schema and redaction/provenance rules;
3. immutable train/validation/test split procedure;
4. Residual Control Bench v0;
5. baseline model identities/configurations;
6. primary/secondary/safety metrics;
7. pass/fail thresholds and statistical plan;
8. benchmark hash/manifest.

No benchmark item may move between splits after results are observed. Corrections require a versioned erratum and a new benchmark version.

## Dataset unit
Canonical record: state → proposed decision → actual decision → outcome → verification → cost → authority.

Required provenance MUST permit replay/audit without requiring secret material. Credentials, tokens, private user data, and unapproved proprietary content MUST NOT enter the corpus.

## Control Bench v0
Target: 1,000 frozen, machine-verifiable situations:
- worker routing: 200
- contract compilation: 150
- evidence sufficiency: 150
- retry/escalate/abort: 100
- budget decisions: 100
- failure classification: 100
- adversarial/malformed state: 100
- stale-state/authority violations: 100

Each item MUST declare expected output, verifier, allowed alternatives (if any), source provenance, contamination group, and difficulty metadata.

## Split policy
Split by mission/incident lineage, not individual messages. Related retries, repairs, derived receipts, duplicated templates, and counterfactuals MUST remain in the same contamination group. Holdout labels remain inaccessible to training jobs.

## Metrics
Primary:
- verified mission success rate;
- verified successful missions per inference dollar;
- verified successful missions per watt where measurable.

Safety metrics are reported separately and MUST NOT be hidden in a composite score:
- false non-escalation rate;
- authority/safety violation rate.

Secondary:
- frontier calls avoided;
- unnecessary escalation rate;
- operator-active minutes;
- latency;
- schema-invalid output rate;
- calibration/error by confidence bucket.

False non-escalation is treated as materially more costly than unnecessary escalation.

## SLM-01 baselines
At minimum:
- existing local 7B deployment;
- one off-the-shelf SLM;
- deterministic/no-model policy where applicable.
Record exact model artifact, quantization, runtime, prompt/template, hardware class, inference settings, and benchmark hash.

## SLM-04 tokenizer ablation
Compare r50k_base, a generic modern tokenizer, and residual-bpe. Measure tokens/trajectory, truncation rate, throughput, memory, and verified task performance. Compression alone is not success; test whether context/model size can be reduced while holding verified performance constant.

## SLM-05 harness ablation
Conditions:
A structured state only
B + contracts
C + epistemic memory
D + deterministic verification
E + failure/repair history
F full Station

Sweep model capacity across available Nano/StationLM sizes, local 7B, and a stronger reference model. Primary analysis measures the left/right shift in model capacity required to cross a preregistered verified-performance threshold.

Ablations MUST remove information/capability explicitly; prompt wording changes alone do not constitute a harness ablation.

## SLM-06 economics
For each routing decision capture selected route, alternatives known at decision time, realized cost, estimated counterfactual cost where defensible, outcome, verification, latency, energy measurement provenance, and escalation correctness. Counterfactual estimates MUST be labeled estimates.

## Safety/authority
StationLM is advisory. Model output has no authority merely because it is schema-valid. Station remains authoritative and fail-closed. Production weights MUST NOT update online. Candidate progression is offline evaluation → shadow → adversarial qualification → human approval → signed artifact → production.

## AX-21 collection
AX-21 may begin collecting observations immediately using observation.schema.json. Collection does not authorize training. Failed trajectories, repairs, operator interventions, empty proposals, stale-state events, and rejected authority attempts are first-class observations.

## Exit criteria
SLM-00 is complete only when the protocol, schema, benchmark specification, split manifest procedure, baseline manifest, thresholds, and prior-art matrix are independently reviewable and content-addressed. Only then may SLM-01 results be used for program decisions.
