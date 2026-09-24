# Reproducibility registry methods

## Purpose and boundaries

The registry indexes R4/R4.1 and selected AX-21 experiments without executing experiments or copying, normalizing, or changing sealed evidence. A registry record is a provenance pointer, not an acceptance authority. External sealed evidence remains authoritative over this documentation.

## Status rules

- `PREREGISTERED`: the protocol, hypotheses, variables, controls, decision rule, stopping rule, and relevant identities were frozen before outcomes were inspected.
- `RETROSPECTIVE`: the record reconstructs a completed activity from existing evidence, including formal-looking qualifications for which a pre-outcome freeze artifact was not established.
- `EXPLORATORY`: an unplanned observation or natural failure generated a hypothesis or bounded finding.

Never convert `RETROSPECTIVE` or `EXPLORATORY` to `PREREGISTERED`. A follow-up may receive a new ID and become preregistered prospectively.

## Registration workflow

1. Assign a unique experiment ID before execution.
2. Complete and hash `PREREGISTRATION_TEMPLATE.md`; commit it before any outcome-bearing run.
3. Freeze code/candidate, model, prompt/config, data/split, environment, seed, metric, threshold, and stopping-rule identities.
4. Register the planned record with outcome `NOT_RUN`, replication count `0`, and the preregistration evidence path/hash.
5. Execute only under separate authorization. Registry documentation never supplies operational authority.
6. Preserve raw evidence and failures append-only. Create a SHA-256 manifest over the declared evidence set.
7. Append results, interventions, deviations, timestamps, and failure classification. Do not overwrite the preregistration.
8. Validate the JSON against `EXPERIMENT_SCHEMA.json` and obtain review before using the record for claims.

## Evidence conventions

`evidence_path` and `evidence_sha256` are ordered arrays; item *n* in one corresponds to item *n* in the other. Use repository-relative paths for committed artifacts, `git:<ref>:<path>` for historical branch records, and `external-sealed:<experiment>/<path>` when sealed material is intentionally outside the repository. A digest authenticates bytes but does not establish completeness, correctness, or authority.

Use `null` when the inspected record does not establish a value. Do not substitute guesses such as an author for the run operator, a branch timestamp for a run timestamp, or zero for missing usage/intervention counts.

## Revisions and models

Record full commit SHA plus tree/parent when candidate ancestry matters. Distinguish the apparatus revision (`code_revision`) from the evaluated artifact (`candidate_revision`). For models, record provider, canonical model name/version, artifact digest, quantization, runtime, prompt/template/config digests, and routing transitions. If any are unavailable, list them in `missing_metadata`.

## Replication accounting

`replication_count` counts outcome-bearing executions of the registered condition, not unit-test repetitions or multiple assertions inside one run. Use `PARTIALLY_REPLICATED` when a repair or altered apparatus repeats only part of the condition. A replication should have a new run identity and evidence manifest while retaining the experiment-family link.

## Deviations and failures

Record every operator intervention and protocol deviation. Classify instrumentation, candidate, environment, provider, evidence, and authorization failures separately. Missing evidence is not a PASS and an apparatus failure is not automatically a candidate failure. Preserve superseded and negative results.

## Current metadata sufficiency

All nine indexed records are marked `INSUFFICIENT` for full reproduction. The main recurring deficits are raw evidence accessibility, exact host/runtime manifests, operator/intervention ledgers, timestamps, seeds, and model artifacts/digests. R4/R4.1 have strong sealed digests and candidate identities but still lack enough repository-accessible operational metadata for an independent exact-condition replay. The prepared R4.1 canary is prospective and comparatively well specified, but cannot run until its deployment-specific inputs and independent authorization exist.

## Literature review

Literature-review status is independent of empirical outcome. `COMPLETE` requires an archived search strategy, sources, scope/date, and synthesis. R4/R4.1 explicitly make no novelty claim; the registry therefore records their review as not started rather than inferring novelty.
