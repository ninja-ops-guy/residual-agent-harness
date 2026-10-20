# Inference-Economics Backlog Acceptance Index

This index is intentionally brief. Detailed acceptance criteria live in `docs/inference-economics-backlog.md`.

## Track exits

- IE-002 exits when inference telemetry is attributable, UNKNOWN-safe, bounded, replayable and non-authoritative.
- IE-003 exits when admission/backpressure is integrated at the approved scheduler seam with atomic reservations, fairness, hysteresis, overload evidence and cancellation/deadline correctness.
- IE-004 exits when context reuse is immutable, provenance-safe, privacy-safe, bounded, invalidated correctly and always subject to required re-verification.
- IE-005 exits when escalation is hard-constraint-first, budget-reserved, bounded and subordinate to existing provider/verifier authority.
- IE-006 exits when empirical routing is hard-filter-first, uncertainty-aware and genuinely replayable from retained decision inputs.
- IE-007 exits when bottleneck classifications are complete/reproducible and any adaptation is bounded, reversible and safely subordinate to existing production authority.
- IE-EVAL exits when the integrated stack has controlled baselines/ablations and measured overhead/cost/latency/goodput evidence without overclaiming.

## Global stop conditions

Any future PR should stop rather than self-weaken if it encounters:
- a protected Factory/M4 ownership conflict;
- a requirement to bypass provider/verifier/integration authority;
- missing authoritative evidence that would otherwise be interpreted as zero/available/safe;
- a need to relax protected tests merely to obtain green CI;
- non-reproducible exact-head evidence;
- an unresolved concurrency, privacy or cancellation defect in the path being promoted.
