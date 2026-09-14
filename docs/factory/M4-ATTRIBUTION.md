# M4 verification failure attribution

Acceptance and attribution are separate decisions. Every non-PASS verification
blocks acceptance, but unavailable infrastructure must never blame a worker.

Attribution requires normal-exit verifier results with typed, nonnegative return
codes. UNKNOWN, launch failure, timeout, output overflow, signals and incomplete
results leave the offending receipt unset and emit no receipt revision/replan.

Counterfactual replay preserves three outcomes: PASS, FAIL and UNKNOWN. A clean
baseline must first PASS. Missing dependencies or ambiguous overlaps make a
subset UNKNOWN, not FAIL. Any UNKNOWN during bisection stops attribution. A final
singleton must reproduce a normal-exit failure before its receipt can be named.
Counterfactual evidence errors also leave attribution unset. This remains a
conservative diagnostic, not proof of unique cause for arbitrary interactions.

`tests/test_factory_m4_attribution.py` covers single/multiple receipt UNKNOWN,
unavailable executables, signal/resource limits, pre-existing baseline failure,
UNKNOWN at each split/singleton, and dependency-incomplete counterfactuals. The
original candidate-specific failure/replan regression remains in
`tests/test_factory_m4_integrator.py` and must continue passing.

This follows review 5199052670 on PR #66. It does not add an OS sandbox or make
trusted-fixture execution safe for untrusted code. Issue #63 remains open. No
Pages presentation, M2 runtime, evaluation adapter, or ownership baseline changes.
