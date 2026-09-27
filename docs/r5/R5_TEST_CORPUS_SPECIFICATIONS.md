# R5 test corpus specifications

Corpora are immutable, content-addressed directories. Each release contains
`corpus.json` with corpus ID/version, generator revision, deterministic seed,
vector IDs, expected oracle class, resource limits, and SHA-256 for every file.
Runtime implementations must not own expected results.

| Corpus ID | Primary gates | Required vector families |
|---|---|---|
| R5-C-FENCE-001 | G01, G05, G09 | acquire/renew/expire/takeover, pause/resume, stale token, skew, reboot, partition |
| R5-C-RECEIPT-001 | G02, G04 | valid signatures; every bound-field mutation; foreign key/epoch; replay; missing/invalid signature |
| R5-C-JSON-001 | G04 | truncation, duplicate keys, type swaps, depth/size limits, UTF-8/Unicode, numeric and canonicalization edges |
| R5-C-STATE-001 | G03, G05 | every allowed/forbidden edge and crash immediately before/after persistence/network boundaries |
| R5-C-SQLITE-001 | G05–G07 | WAL/commit/fsync/checkpoint faults, BUSY/LOCKED/FULL/IOERR, page/WAL/schema corruption |
| R5-C-CLOCK-001 | G08, G10, G13 | monotonic progression, wall jumps/rollback, expiry boundaries, delayed observation |
| R5-C-TOPOLOGY-001 | G09, G12 | supported/unsupported hosts, asymmetric partitions, lag, failover, stale replicas, DR |
| R5-C-TELEMETRY-001 | G10 | loss, duplication, reordering, exporter outage, cardinality payloads, secret/message tokens |
| R5-C-VERSION-001 | G02, G11–G13 | major/minor/feature pairs, unknown fields, downgrade stripping, newer rows, rollback readers |
| R5-C-RETENTION-001 | G13 | lookup/GC race, horizon edges, old backup, policy shrink, legal deletion, pressure |
| R5-C-EFFECT-001 | G12–G14 | producer/consumer crash points, duplicates, reorder, restore replay, fanout partials |
| R5-C-EVIDENCE-001 | G15–G17 | missing/extra/duplicate artifacts, hash/path attacks, stale receipts, wrong trees, retry replacement |

## Fixture tiers

- **Positive:** the smallest valid vector and one realistic composed vector.
- **Negative:** one controlled violated precondition with a single expected
  reason code and zero unauthorized state/effect delta.
- **Adversarial:** bounded combinations and schedule permutations intended to
  expose interaction faults. Pairwise generation is the minimum; critical
  persistence/fencing boundaries require full declared cross-product coverage.

## Corpus admission

A corpus revision is admitted only when its generator is deterministic, all
vectors have unique stable IDs, expected outcomes are reviewed independently,
limits prevent decompression/log/memory amplification, secret-like tokens are
synthetic, and two clean generations have identical manifests and payload
hashes. Corrections create a new version and retain the prior version and any
counterexamples.

## Evidence per vector

Record vector ID/hash, seed and schedule, fault locations, candidate/harness
identity, ordered actions, pre/post durable state hashes, network/effect counts,
oracle output and reason code, duration/resource bounds, redaction result, and
artifact hashes. Aggregate reports may summarize but never replace raw vector
evidence.

