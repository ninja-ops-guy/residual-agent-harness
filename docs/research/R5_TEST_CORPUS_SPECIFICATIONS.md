# R5 test corpus specifications

Status: specifications only; fixtures are not implemented or executed here

## Corpus contract

Every fixture has a stable ID, schema version, generator revision or literal bytes, expected oracle result, maximum resource envelope, and SHA-256 entry in the frozen qualification manifest. Generated cases must record their seed and generation algorithm. Shrunk counterexamples receive new IDs and remain linked to their source case.

Fixtures contain synthetic messages and disposable identities only. Secrets, production receipts, production databases, and R4/R4.1 evidence are prohibited inputs.

## Manifest and governance corpus

| Fixture | Class | Specification | Expected result |
|---|---|---|---|
| QI-VALID-MANIFEST | positive | complete pinned candidate/harness/corpus/oracle/gate inventory | manifest valid |
| QI-MISSING-ARTIFACT | negative | remove one required artifact from inventory | reject before run |
| QI-POSTHOC-ORACLE-SWAP | adversarial | change oracle hash after outcome exists | invalidate run |
| EG-COMPLETE-BUNDLE | positive | raw records, summary, provenance, failures, redaction report, hashes | reproducible PASS |
| EG-MISSING-FAILURE | negative | omit a known failing negative control | reject incomplete bundle |
| EG-SUMMARY-TAMPER | adversarial | alter summary without altering raw trace | detect divergence |

## Version/protocol corpus

`PV-COMPATIBLE-MATRIX` enumerates every declared sender, Station, stored-row, and receipt version/feature combination. It includes rolling upgrade, restart during upgrade, and qualified rollback. `PV-UNKNOWN-MAJOR` introduces an unknown major at each boundary. `PV-DOWNGRADE-STRIP-BINDING` advertises compatibility while omitting a mandatory receipt binding. Only declared compatible cells may mutate state.

## Receipt corpus

Start from `RCPT-VALID-BOUND`, a canonically encoded authenticated receipt bound to one synthetic issuer, epoch, protocol, project, operation, request digest, event ID, sequence, and outcome.

The named negative controls are `RCPT-MISSING-SIGNATURE`, `RCPT-WRONG-PROJECT`, `RCPT-WRONG-OPERATION`, and `RCPT-TRUNCATED`. Each changes only the named condition from the valid control so its rejection reason is unambiguous.

`RCPT-FIELD-MUTATION-MATRIX` changes exactly one bound field per vector, including null, missing, wrong type, alternate normalized form, minimum/maximum integer, and valid foreign value. `RCPT-FOREIGN-EPOCH-REPLAY` replays a valid receipt across trust epoch and Station identity. `RCPT-CROSS-PROJECT-COLLISION` uses the same operation ID in two projects and attempts reciprocal substitution.

`RCPT-PARSER-CORPUS` includes:

- empty, truncated, invalid-UTF-8, deeply nested, oversized, and trailing-data bodies;
- duplicate keys before and after normalization;
- numeric overflow, negative sequence, float where integer is required, and Boolean-as-integer;
- Unicode confusables, non-normalized text, escaped separators, and canonicalization variants;
- missing/extra fields, null mandatory fields, arrays/objects replacing scalars;
- valid authentication over semantically wrong project, operation, digest, event, version, or outcome;
- corrupted stored JSON and valid JSON with a mismatched at-rest digest.

Each parser vector declares maximum bytes, nesting, parse time, expected reason code, expected durable state, and expected zero/one network actions.

## State-machine and crash corpus

`SM-HAPPY-PATH` covers enqueue, send, committed ACK, verified persistence, and terminal ACK. `SM-RECEIPT-FOUND` covers remote commit, ACK loss, restart, lookup, verified local recovery, and zero retransmission. `SM-ILLEGAL-TRANSITION` attempts every undeclared edge in the frozen transition table.

`SM-CRASH-POINT-MATRIX` places a deterministic stop immediately before and after:

1. enqueue transaction;
2. lease acquisition;
3. transition to sending;
4. request write start and completion;
5. response read start and completion;
6. transition to indeterminate;
7. receipt lookup start and completion;
8. receipt verification;
9. ACK transaction begin, WAL append, commit, and durability barrier;
10. terminal observation emission.

Every case records pre-image hash, stop point, restart image, transition journal, ordered network trace, and expected state set.

## Lease and topology corpus

`LEASE-SINGLE-OWNER` is the positive acquisition/renew/release control. `LEASE-STALE-TOKEN` attempts send and transition with an older token. `LEASE-PAUSE-TAKEOVER-RESUME` pauses owner A past expiry, grants B a higher token, advances with B, then resumes A. `LEASE-CONTENDED-START` starts a fixed number of processes at one barrier and repeats with deterministic schedules.

`TOPO-SUPPORTED-FAILOVER` enumerates each topology the implementation claims to support. `TOPO-UNSUPPORTED-SHAREDFS` presents file locking/durability capabilities outside the support manifest. `TOPO-SPLIT-BRAIN-PARTITION` independently partitions owner-to-lease and owner-to-Station paths, then heals them in both orders. Each case requires an explicit capability verdict before send.

## ACK durability and storage corpus

`ACK-COMMIT-DURABLE` is the positive verified-receipt transaction. `ACK-UNVERIFIED-RECEIPT` tries to enter ACKED without a verification decision. `ACK-CRASH-BOUNDARY-MATRIX` combines the ACK-specific points above with disposable SQLite journal modes declared by the implementation. `ACK-STALE-OWNER-RACE` changes the fence during receipt verification and at every ACK transaction boundary.

`SQLITE-CONTENTION-RECOVERS` holds read/write locks for deterministic intervals below and above the declared busy budget. `SQLITE-FULL-BEFORE-SEND` injects FULL before durable pre-send state. `SQLITE-ERROR-BOUNDARY-MATRIX` injects BUSY, LOCKED, FULL, IOERR, READONLY, CANTOPEN, quota, inode, and permission failures at enqueue, transition, lookup persistence, ACK, quarantine, telemetry, and evidence writes.

## Corruption corpus

`CORRUPT-UNAFFECTED-ROW` pairs one known-valid row with a separately corrupt record to test justified isolation. `CORRUPT-PAYLOAD-DIGEST` changes payload bytes without updating the digest. `CORRUPT-SQLITE-CORPUS` contains content-addressed copies with single-page flips, truncation, damaged WAL, schema/version mutation, impossible state, receipt mutation, missing index, and partial-backup combinations.

The oracle must never edit the only corrupt copy. It hashes and preserves source bytes before opening a disposable working copy.

## Stale-policy corpus

`STALE-AUTHORIZED-RESUME` uses a valid operator authorization and current policy. `STALE-AGE-ONLY-RESEND` crosses the threshold without lookup or disposition. `STALE-CLOCK-ANOMALY-MATRIX` combines wall-clock rollback/jump, monotonic reset across reboot, delayed receipt, policy update, abandoned project, and repeated restart. Expected outcomes distinguish queryable, reconciling, cancelled, resumed, quarantined, and indeterminate.

## Observability corpus

`OBS-MIXED-RECOVERY` is a frozen journal containing each state, receipt decision, fence rejection, contention outcome, quarantine, and authorized disposition. `OBS-MISSING-TRANSITION` removes one observation while leaving durable state unchanged. `OBS-HOSTILE-LABEL-CORPUS` supplies long values, high-cardinality IDs, control characters, message/secret-like strings, and confusables. `OBS-EXPORTER-OUTAGE` drops, duplicates, reorders, and delays export while retaining journal truth.

The expected metric vector, label cardinality ceiling, redaction decisions, and alert firing times are fixture data, not implementation-computed expectations.

## Distributed lookup corpus

`LOOKUP-AUTHORITATIVE-FOUND` and `LOOKUP-AUTHORITATIVE-ABSENT` carry valid authority/consistency proof. `LOOKUP-STALE-REPLICA-ABSENT` returns absence from a replica known to lag the commit index. `LOOKUP-PARTITION-FAILOVER-MATRIX` covers leader loss before/after commit, asymmetric partition, stale cache, index loss with retained event, disaster-recovery promotion, and heal ordering.

Every lookup case declares the only allowed result class: found, authoritative absence, non-authoritative, or indeterminate. Only the first two may support a state decision, and absence alone does not bypass the rest of the send-eligibility policy.

## Retention and GC corpus

`GC-EXPIRED-WITH-TOMBSTONE` is the positive expiry case. `GC-EARLY-DELETE` removes uniqueness evidence while a retry remains admissible. `GC-RACE-RESTORE-MATRIX` races lookup and retry against mark, tombstone, compact, and policy-change points, then restores snapshots from before each point. It includes legal-deletion and storage-pressure policy outcomes without prescribing policy beyond requiring an explicit auditable result.

## External-effect corpus

`EFFECT-IDEMPOTENT-CONSUMER` consumes a stable effect ID transactionally. `EFFECT-NONIDEMPOTENT-CONSUMER` demonstrates the bounded counterexample when the downstream effect and ACK are not atomic/idempotent. `EFFECT-CRASH-BOUNDARY-MODEL` enumerates delivery, effect, offset/ACK, replay, reordering, backup restore, and partial multi-sink fanout boundaries.

The negative consumer fixture is expected to falsify a universal exactly-once claim. A harness that reports it as PASS is invalid.

## Convergence corpus

`CONV-ALL-PHASES-PASS` contains one internally consistent synthetic set of all requirement and phase manifests. `CONV-MISSING-UPSTREAM-GATE` removes an upstream gate. `CONV-RETRY-TO-GREEN` replaces a retained failed run with a later pass under the same identity. `CONV-DAG-CYCLE` introduces a dependency cycle. Only the complete acyclic, append-only lineage may converge.

## Corpus acceptance checklist

- All referenced fixture IDs exist exactly once.
- Positive, negative, and adversarial classes are present for every requirement.
- Expected outcomes are authored before execution and hashed.
- Bounds exist for bytes, cases, processes, time, retries, and generated cardinality.
- Synthetic identities cannot resolve to production projects or keys.
- Fixture generation is deterministic from retained seeds.
- Failures and minimized counterexamples are append-only.
- Corpus updates require a new version and invalidate only the dependent qualification suffix explicitly identified by the DAG.
