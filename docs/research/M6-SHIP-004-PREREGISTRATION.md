# M6-SHIP-004 Preregistration — Minimal Context Real-Repository Shipping

M6-SHIP-003 established that a ~32.6 KB local-model request can hit the 300 s provider timeout before producing a candidate. The broad context was not required for this contract.

M6-SHIP-004 keeps:
- the same ImprovementSpec requirements;
- the same external immutable verifier and verifier hash;
- qwen2.5-coder:7b;
- the same five-attempt, token, wall-clock, review, receipt, integration, and export gates.

The only task-context change is removal of unrelated `residual/core.py` and `residual/goalspec.py`.

Read-only context is now only:
`scripts/m6_ship_improvementspec_check.py`

## Hypothesis

Removing unrelated source context will reduce request size/latency enough for the local model to execute reliably, while the external verifier provides all contract detail required for bounded repair.

## Research endpoint

Record request_bytes and elapsed_ms for every call. A successful task must still pass the identical semantic verifier, review, receipt, and release gates.
