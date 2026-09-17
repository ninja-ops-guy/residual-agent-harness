# Acceptance Status Values

Use only these states in release evidence:

- PASS — directly exercised and satisfied.
- FAIL — directly exercised and failed.
- NOT_RUN — intentionally not exercised.
- UNKNOWN — evidence insufficient or ambiguous.
- BLOCKED — required evidence cannot currently be obtained or a prerequisite failed.

Do not convert NOT_RUN/UNKNOWN/BLOCKED to PASS based on adjacent layers.
