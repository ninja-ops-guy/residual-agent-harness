# M6-SHIP-003 Preregistration — Immutable External Acceptance Verifier

M6-SHIP-002 failed before model execution because the detailed inline `python -c` verifier exceeded Station's 2,000-character argv element bound.

M6-SHIP-003 preserves the original roadmap contract and acceptance semantics but moves the behavioral verifier into a versioned read-only repository file:

`scripts/m6_ship_improvementspec_check.py`

The candidate receives that verifier as read-only context. Its only writable path remains:

`residual/improvement/spec.py`

The verifier explicitly inserts the candidate repository root into sys.path so it cannot accidentally test the outer editable installation.

## Hypothesis

A versioned external verifier provides actionable repair evidence and avoids inline-command size limits while keeping acceptance independent of the candidate.

## Unchanged

- qwen2.5-coder:7b
- one local worker
- 1600 output-token ceiling
- 5 bounded attempts
- 30,000-token budget
- 1,800 s mission wall-clock budget
- local independent review
- receipt/integration/export requirements
- no cloud fallback
- no candidate authority over verifier or promotion

## Success

The task must pass compile + external contract verifier, receive review approval, integrate with a verification receipt, and export the exact generated source.
