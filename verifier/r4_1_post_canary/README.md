# R4.1 post-canary promotion evidence gate

This package evaluates evidence from a separately authorized, already-completed
R4.1 canary. It does not run a canary, roll back, deploy, or promote anything.

The verifier emits exactly one disposition:

- `PROMOTION_ELIGIBLE`: complete evidence satisfies every gate. This only permits
  a later human promotion decision; it is never promotion authority.
- `CANARY_FAILED`: complete, internally consistent evidence proves a functional
  or rollback-rehearsal acceptance failure without a presently unsafe state.
- `EVIDENCE_INCOMPLETE`: evidence is missing, malformed, contradictory,
  hash-invalid, outside the authorized scope, or otherwise unverifiable.
- `ROLLBACK_REQUIRED`: verified evidence proves an unsafe post-canary state,
  unauthorized production or credential mutation, protected-service
  instability, an exceeded execution bound, or an unclosed receiver effect.

## Invocation

```bash
python verifier/r4_1_post_canary/verify.py \
  --evidence /sealed/canary-run \
  --authorization-sha256 <independently-recorded-receipt-sha256> \
  --decision /tmp/promotion-decision.json \
  --rollback-decision /tmp/rollback-decision.json \
  --report /tmp/promotion-report.md
```

The evidence directory must contain `canary-evidence.json` and every file in its
`artifacts` manifest. Paths must be relative, normalized, and remain beneath the
evidence directory. The authorization receipt is itself a manifested artifact;
the independently supplied SHA-256 is the trust anchor that prevents a bundle
from self-authorizing.

Outputs are newly generated evaluation records. They must not be written inside
the sealed evidence directory. Exit status is `0` only for
`PROMOTION_ELIGIBLE`; all other dispositions exit `2`.

The JSON schemas are normative for producers. The verifier deliberately repeats
critical validation using only the Python standard library, so a missing schema
validator cannot turn malformed evidence into a pass.

