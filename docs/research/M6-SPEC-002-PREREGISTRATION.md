# M6-SPEC-002 Preregistration — Model Capability Replication

## Research question
Does increasing implementation-agent capability allow RESIDUAL to complete the same bounded ImprovementSpec self-hosting task while the independent acceptance boundary remains unchanged?

## Relationship to M6-SPEC-001
M6-SPEC-001 is closed as an authoritative failed trial. Its specification and behavioral checks are frozen. M6-SPEC-002 is a new experiment and MUST NOT overwrite or reinterpret M6-SPEC-001.

## Independent variable
Implementation/review model:
- M6-SPEC-001: qwen2.5-coder:1.5b
- M6-SPEC-002: qwen2.5-coder:7b

## Controlled variables
- RESIDUAL baseline: 699e2869e294fe157b4bfd73a272057683a2f7e0
- Python: 3.12
- provider: local Ollama
- workers: 1
- target specification: unchanged from M6-SPEC-001
- target path: residual/improvement/spec.py
- behavioral and negative-path checks: unchanged
- output-token ceiling: 1600
- requested batch token/wall-clock settings: unchanged
- protected boundaries and success criteria: unchanged
- first run is authoritative; no retry may replace a failed trial

## Primary endpoint
Complete accepted implementation:
- integrated == 1
- task state == integrated
- every behavioral check passes
- model review approved
- verification receipt exists
- generated source exists in export
- export_error is null

## Secondary endpoints
- first-pass correctness
- repair count
- provider calls
- input/output/reported tokens
- wall clock
- truncation
- final brake/outcome
- false acceptance (any integrated candidate failing frozen checks; target = zero)

## Failure policy
Infrastructure failure and model failure are retained and reported. A corrected experiment requires a new numbered trial/experiment and cannot replace the authoritative first run.

## Interpretation
Success supports bounded recursive-development feasibility for this task/model combination; it does not establish autonomous improvement, general reliability, or authority to promote a successor.
