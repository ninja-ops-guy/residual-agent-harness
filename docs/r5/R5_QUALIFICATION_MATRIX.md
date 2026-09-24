# R5 qualification matrix

Status: planning and test design only. All gates are external, fail closed, and
non-promoting. The frozen R4.1 candidate remains HEAD
`8701367db6d3202f24b3eb9f4696b0cadf657985`, tree
`79bfe6ed1743907065ed44aeb9c460c47527e0c6`.

The normative requirement fields and edges are in `R5_DAG.json`. This matrix is
the human review index. `PASS` requires all named positive, negative, and
adversarial fixture families, complete hashes, zero undeclared skips, and a
matching candidate/harness/corpus identity.

| Gate | Requirement | Category | Phase | Deterministic pass oracle | Required evidence |
|---|---|---:|---:|---|---|
| R5-G01 | SC-001 fencing | B | P2 | one maximal-fence authority; zero stale sends/mutations | lease rows, timelines, action trace, effect ledger, DB image |
| R5-G02 | SC-002 receipt authority | C | P1 | only exact authorized bound receipt verifies | signed vectors, trust epochs, mutation decisions, states |
| R5-G03 | SC-003 state machine | A | P2 | trace accepted by graph; restart matches model | graph, crash matrix, snapshots, model report |
| R5-G04 | SC-004 hostile receipts | C | P2 | stable rejection reasons; zero false ACK | corpus hashes, parser limits, deltas, redacted logs |
| R5-G05 | SC-005 ACK durability | B | P3 | prior safe state or complete verified ACK | fault map, SQLite settings/integrity, row, fence, trace |
| R5-G06 | SC-006 corruption | F | P3 | no action; exact quarantine; forensic bytes retained | image hashes, integrity output, quarantine/recovery reports |
| R5-G07 | SC-007 storage faults | F | P3 | no unjournaled effect/false success; bounded recovery | capacity, injections, API result, snapshots, trace |
| R5-G08 | SC-008 stale policy | F | P3 | only authorized explicit inputs determine disposition | policy, clocks, authorization, history, final state |
| R5-G09 | SC-009 topology | B | P4 | one fenced lineage or pre-send unsupported result | topology, partitions, leases, node traces, effects |
| R5-G10 | SC-010 observability | E | P4 | metrics reconcile; bounded labels; zero leakage | schema, scrape, reconciliation, redaction, alerts |
| R5-G11 | SC-011 versioning | A | P1 | matrix result exactly; incompatible pairs have no effect | registry, transcripts, row versions, rollback results |
| R5-G12 | SC-012 lookup authority | A | P4 | authority model match; no absence-driven repost | authority manifest, schedules, transcripts, convergence |
| R5-G13 | SC-013 retention/GC | C | P4 | uniqueness survives horizon/races; bounded storage | policy, GC journal, tombstones, restore traces, growth |
| R5-G14 | SC-014 claim boundary | A | P5 | model property and trace refinement hold | model, checker, refinement, schedules, effect ledger |
| R5-G15 | SC-015 evidence governance | D | P0 | only complete authorized hash-bound set verifies | schemas, identities, authorization, manifest, failure ledger |
| R5-G16 | SC-016 deterministic harness | G | P0 | repeated normalized traces and decisions are identical | seeds, schedules, registry, two traces, normalized diff |
| R5-G17 | SC-017 convergence | G | P5 | exact topological closure on one tree; no weakened gate | phase receipts, DAG hash, inventory, cross-phase suite |

## Phase gates

| Gate | Input closure | Independent qualification decision |
|---|---|---|
| R5-PG0 | G15, G16 | Evidence and fault infrastructure are reproducible; no runtime claim. |
| R5-PG1 | PG0, G11, G02 | Version negotiation and authenticated receipt authority pass as an isolated protocol slice. |
| R5-PG2 | PG0, PG1, G01, G03, G04 | Fenced local recovery and explicit reconciliation pass every receipt/crash schedule. |
| R5-PG3 | PG2, G05–G08 | Persistence, corruption, storage, and stale-policy failures remain safe and recoverable. |
| R5-PG4 | PG3, G09, G10, G12, G13 | Declared topologies, telemetry, authority-aware lookup, and retention compose without duplicate effects. |
| R5-PG5 | PG0–PG4, G14, G17 | Formal claim and release evidence close on one immutable tree with tested rollback edges. |

## Result rules

- A gate result is one of `PASS`, `FAIL`, `EVIDENCE_INCOMPLETE`, or
  `NOT_RUN`. Only `PASS` satisfies an edge.
- A phase is independently qualifiable when its phase gate can evaluate a
  pinned candidate containing that phase plus immutable receipts for all prior
  phase gates. Later-phase code is neither required nor permitted in its claim.
- Missing fixtures, unregistered skips, malformed evidence, hash mismatch,
  candidate drift, or retry that discards a prior counterexample is
  `EVIDENCE_INCOMPLETE`, never `PASS`.
- Safety and liveness are reported separately. Safe unavailability is not a
  liveness pass; responsive duplication is not a safety pass.
- No gate merges, deploys, promotes, rotates credentials, or operates R4.1.

