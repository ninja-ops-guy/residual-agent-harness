# M6-SPEC-005 Preregistration — Post-Remediation Integrated Validation

## Purpose
Validate the corrected RESIDUAL repair loop as an integrated system after applying lessons from M6-SPEC-001 through M6-SPEC-004.

This is not a one-variable causal experiment. It is a post-remediation validation run intended to answer whether the repaired harness can now complete the same frozen self-hosting specification under the recommended local coding configuration.

## Harness under test
Exact harness head:
`e7488199ee238f04ef1547338199096389047b2e`

This head applies:
1. previous failed writable files as bounded repair context;
2. durable hashes binding the repair context;
3. explicit transport-JSON versus literal source-code guidance;
4. a single shared five-attempt task ceiling used by both Store and Mission Control;
5. regression coverage proving a fourth attempt can still pass unchanged checks, review, receipt issuance, and integration.

No verifier, M4, review authority, receipt semantics, integration checks, quarantine policy, or promotion authority is weakened.

## Frozen task
The ImprovementSpec implementation instruction and deterministic behavioral/negative-path checks are unchanged from M6-SPEC-001.

## Runtime configuration
- Python 3.12
- local Ollama
- model: `qwen2.5-coder:7b`
- workers: 1
- max output tokens: 4096
- batch max passes: 5
- token budget: 30000
- wall-clock budget: 600 s
- local review
- no cloud fallback
- first authoritative model run is retained pass or fail

The 7B model is the project's recommended local coding baseline. The larger output ceiling avoids treating an avoidable truncation limit as a harness-quality result.

## Primary endpoint
A trial succeeds only if:
- batch.integrated == 1
- task.state == integrated
- all unchanged behavioral checks pass
- review.approved == true
- verification_receipt exists
- generated source is present in the release export
- export_error is null

## Secondary measurements
- number of implementation attempts
- whether repair context was exercised
- candidate patch and check artifacts per attempt
- reviewer result
- integration receipt
- provider calls
- input/output/reported tokens
- request bytes
- mission wall clock
- brake/outcome
- generated-source SHA-256
- false acceptance, target zero

## Interpretation
Success demonstrates that the remediated harness can perform this bounded self-hosting task under the recommended local configuration. It does not establish general autonomous recursive self-improvement or authority to self-promote.

Failure remains authoritative and must be analyzed from retained per-attempt evidence before another remediation trial is created.
