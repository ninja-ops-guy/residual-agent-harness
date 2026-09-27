# M6-SPEC-007G Preregistration — General-Model Scientist

## Purpose

M6-SPEC-007D through 007F established that typed structured output solves representation errors, but the coding model repeatedly misclassified an already-measured metric as a MeasurementGap.

## Independent variable

Scientist/reviewer model:
- prior: qwen2.5-coder:7b
- this trial: qwen2.5:7b

## Preserved

- same aggregate EvidenceSnapshot and raw evidence hashes;
- no supplied improvement question, target metric, intervention, or hypothesis;
- same typed proposal schema used by 007D;
- same deterministic host verifier;
- same independent semantic review stage;
- same human approval requirement;
- no implementation, Git, evaluator, M4, or promotion authority.

## Hypothesis

A general instruction model is better suited than a coding-specialized model to evidence interpretation and hypothesis formation, while the deterministic verifier remains the authority for admissibility.

## Success

The proposal must:
1. complete as typed structured output;
2. pass mechanical evidence admission with zero errors;
3. receive semantic reviewer approval;
4. receive a cryptographic admission receipt.

Any mechanically valid but reviewer-rejected proposal remains inadmissible and cannot advance to M6-008.
