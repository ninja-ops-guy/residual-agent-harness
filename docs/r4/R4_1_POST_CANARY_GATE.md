# R4.1 post-canary promotion gate design

Status: design/preparation only. Candidate HEAD
`8701367db6d3202f24b3eb9f4696b0cadf657985`, tree
`79bfe6ed1743907065ed44aeb9c460c47527e0c6`.

## Decision model

The verifier is a pure evidence consumer. It opens no network connections and
contains no deployment or rollback primitive. Evaluation uses this precedence:

1. `ROLLBACK_REQUIRED` when verified evidence proves a safety trigger: protected
   service instability, any production or credential mutation, an exceeded
   authorization bound, or a receiver-side-effect cardinality other than one.
2. `EVIDENCE_INCOMPLETE` when no verified rollback trigger exists and any input
   is missing, malformed, contradictory, hash-invalid, outside the authorization
   window/scope, or unverifiable.
3. `CANARY_FAILED` when the evidence is complete but a functional acceptance or
   rollback-rehearsal requirement fails without proving a currently unsafe state.
4. `PROMOTION_ELIGIBLE` only when every check passes.

This ordering avoids hiding an evidenced unsafe state behind an unrelated
missing field. Unverified claims never trigger an automatic action: they fail
closed as `EVIDENCE_INCOMPLETE`.

## Objective evidence contract

`canary-evidence.json` binds the candidate identity, pre/post snapshots, a
contiguous ordered event trace, stable operation ID, receiver effect ledger,
durable outbox journal, injected crash/restart trace, protected-service
snapshots, mutation audits, execution bounds, rollback rehearsal, operator log,
and authorization scope. Every referenced source file must occur exactly once in
the artifact manifest with byte size and SHA-256.

The canary authorization receipt must be captured before execution, name the
same run/environment/candidate and bounded UTC window, authorize canary only,
and explicitly deny promotion authority. Its SHA-256 is passed to the verifier
from an independent control-plane record. A receipt contained only inside the
bundle cannot authorize itself.

The event sequence required for eligibility is:

```text
outbox_durable -> network_send -> receiver_effect -> receipt_durable
  -> crash -> restart -> receipt_lookup -> outbox_ack
```

This proves durable-before-network ordering and receipt-first restart
reconciliation. All event, receiver, outbox, and restart operation IDs must be
identical. Exactly one distinct receiver side effect must exist before and after
restart.

Prestate and poststate use digests rather than narrative attestations. Separate
artifact records retain the underlying snapshots. Protected service and
credential digests must remain equal; mutation audits must report zero. The
rollback rehearsal must restore the expected digest within its declared bound.

## Determinism and fail-closed behavior

Inputs are parsed as JSON, timestamps must be UTC `Z`, paths must be normalized
relative paths, symlinks are rejected, event sequence numbers must be contiguous,
and all hashes are lowercase SHA-256. Decision JSON is serialized with sorted
keys and compact separators. No wall-clock value is added, so identical bytes,
trust anchor, and verifier version produce identical outputs.

Decision and report outputs are created exclusively and cannot overwrite prior
records. They must be directed outside the sealed evidence directory. The
operator archives the verifier source revision and hashes the generated outputs
afterward.

## Human boundary

`PROMOTION_ELIGIBLE` is an evidence result, not an action or approval. A human
must review the report and make a later, separately authorized promotion
decision. No successful verifier path invokes deployment or promotion.

