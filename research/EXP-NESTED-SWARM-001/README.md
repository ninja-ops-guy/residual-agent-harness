# EXP-NESTED-SWARM-001 — Governed Nested Agent Runtime Evaluation

## Research question

Can RESIDUAL serve as a governance, verification, and evidence layer around independently agentic systems and swarms while preserving or improving useful task performance?

This repository addition is the preregistration/evidence machinery, **not a benchmark result**. Measured claims begin only after real trials are run against a frozen corpus.

## Frozen arms

| Arm | Runtime | Governance | Nested |
| --- | --- | --- | --- |
| A | RESIDUAL native swarm | RESIDUAL | no |
| B | Moonshot/Kimi direct | provider-native | no |
| C | Kimi Claw/OpenClaw | provider-native | no |
| D | RESIDUAL with Moonshot + Kimi Claw workers | RESIDUAL | yes |

The same frozen task corpus, acceptance checks, external test harness, model/provider revisions, and trial count must be used across arms. Failures are retained; failed trials are not silently rerun away.

## Captured metrics

V1 records task success, verifier pass rate, wall-clock latency, input/output tokens, API cost, provider calls, retries, evidence requests, failed tool calls, human interventions, integration conflicts, duplicate work, convergence iterations, and provenance completeness.

Every trial binds the preregistration hash, task hash, runtime revision, non-secret provider/model snapshot, WorkerContract hash, RESIDUAL trace root, complete metric vector, and outcome/failure code.

## Procedure

1. Freeze a representative task corpus and calculate its SHA-256.
2. Call `build_manifest(...)` before measured trials.
3. Execute each task under A/B/C/D without changing acceptance criteria.
4. Convert telemetry into `TrialRecord` and persist it with `record_trial`.
5. Run `verify_trial` before accepting evidence.
6. Run `summarize_experiment` only after all preregistered arm/repeat cells exist.
7. Export report JSON plus raw traces and receipts for statistical analysis and paper figures.

## Claim discipline

A completed report supports descriptive comparisons for the exact frozen corpus and runtime revisions. It does not by itself establish general superiority of RESIDUAL, Moonshot, Kimi, OpenClaw, or nested swarms. Paper claims must state the task population, controls, uncertainty, exclusions, and statistical procedure.

Predictions are not evidence.
