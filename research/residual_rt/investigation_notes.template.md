# RESIDUAL-RT Pilot Investigation Notes

Trial ID:

Raw result SHA-256:

Investigator:

Investigation date:

## 1. Apparatus validity

- Exact source revision:
- Manifest complete:
- Result hash verified:
- Protocol identity stable:
- Provider/model identity stable:
- Any non-lab target observed:
- Infrastructure anomalies:

Assessment:

## 2. Model protocol compliance

- Total runs:
- Scored runs:
- Invalid proposal runs:
- Provider-error runs:
- Scored fraction:
- Mean proposals per scored run:

Notable malformed outputs:

## 3. RT0 vs RT5 summary

| Metric | RT0 | RT5 | Observation |
|---|---:|---:|---|
| accepted correctness | | | |
| acceptance coverage | | | |
| false acceptance rate | | | |
| scope violation execution rate | | | |
| unauthorized high-risk execution rate | | | |

Do not treat higher accepted correctness as an improvement unless acceptance coverage remains useful.

## 4. Marginal mechanism observations

### RT0 -> RT1: scope gate

What changed?

### RT1 -> RT2: evidence gate

What changed?

### RT2 -> RT3: verifier gate

What changed?

### RT3 -> RT4: epistemic memory

What changed?

### RT4 -> RT5: risk-tiered HITL

What changed?

## 5. Engagement-by-engagement review

### PB1-web-exposure

Model behavior:

Unexpected behavior:

### PB2-api-auth

Model behavior:

Unexpected behavior:

### PB3-segmentation-observation

Model behavior:

Unexpected behavior:

### PB4-risk-tiered-change

Model behavior:

Unexpected behavior:

## 6. Error analysis

Dominant false-positive pattern:

Dominant false-negative pattern:

Dominant verifier-UNKNOWN pattern:

Scope drift pattern:

High-risk request pattern:

Malformed-output pattern:

## 7. Cost and latency

- Mean elapsed ms:
- Reported input tokens:
- Reported output tokens:
- Known direct cost:
- Cost-unknown runs:

## 8. Reproducibility / repeat behavior

Were proposal patterns stable across repeats?

Were there obvious seed-dependent changes?

Any result that should be tested with more repeats?

## 9. Protocol changes suggested by this pilot

List changes, but do **not** apply them to this completed trial identity.

1.
2.
3.

## 10. Overall pilot verdict

Choose exactly one:

- INFORMATIVE
- INFORMATIVE-NEGATIVE
- INFRASTRUCTURE-INVALID
- INCONCLUSIVE

Verdict:

Rationale:

## 11. Confirmatory recommendation

Proceed to larger Phase B confirmatory study?

What must be frozen or repaired first?
