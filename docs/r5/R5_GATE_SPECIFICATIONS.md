# R5 gate specifications

## Common gate contract

Every gate consumes a sealed run directory and an external authorization trust
anchor. Required envelope fields are gate ID/version, candidate HEAD/tree,
harness HEAD/tree, dependency gate receipts, fixture/corpus IDs and hashes,
environment identity, start/end bounds, raw artifact manifest, decision, and
operator interventions. The verifier is external and read-only.

Common negative controls: wrong candidate, wrong gate ID, stale dependency
receipt, omitted fixture, duplicate manifest path, path traversal, symlink,
digest mismatch, malformed JSON, unknown schema, unregistered skip, timeout,
and replacement of an earlier failed attempt. Each must fail closed.

## Requirement gates

- **R5-G01 / fencing:** enumerate acquisition, renewal, expiry, takeover, and
  stale-resume cut points. Pass only with one maximal-token action lineage.
- **R5-G02 / receipt authority:** verify the signed-field mutation matrix,
  foreign trust epochs, replay contexts, and canonicalization variants.
- **R5-G03 / state machine:** execute pre/post crash points for every allowed
  transition and reject every graph edge not in the frozen transition table.
- **R5-G04 / receipt robustness:** run the hostile receipt corpus through HTTP,
  parser, persisted-load, and restart entry points under size/time bounds.
- **R5-G05 / ACK persistence:** inject kill and storage faults at transaction,
  WAL, fsync, and checkpoint boundaries, including stale-fence races.
- **R5-G06 / corruption:** mutate page, WAL, schema, payload, digest, and receipt
  layers; compare quarantine and forensic outputs to corpus expectations.
- **R5-G07 / storage:** exhaust bytes/inodes and inject SQLite errors at every
  persistence point; require safe checkpoint recovery after restoration.
- **R5-G08 / stale policy:** combine clock anomalies with delayed receipts and
  authorized/unauthorized inspect, reconcile, resume, and cancel actions.
- **R5-G09 / topology:** execute supported and unsupported topology manifests
  under independent lease/Station partitions, reboot, and stale-node resume.
- **R5-G10 / observability:** reconcile journal and telemetry under drop,
  duplicate, exporter outage, hostile labels, and secret-bearing content.
- **R5-G11 / versioning:** run the complete declared version/feature pair matrix
  over send, lookup, restart, upgrade, downgrade, and rollback.
- **R5-G12 / lookup authority:** model replica lag, leader loss, partitions,
  stale cache, lost index, DR, and delayed authoritative answers.
- **R5-G13 / retention:** race lookup/recovery/GC, restore old clients, cross
  replay horizons, shrink policy, and measure storage bounds.
- **R5-G14 / formal claim:** boundedly explore all producer-to-consumer crash
  points and refine implementation traces to the published safety property.
- **R5-G15 / evidence governance:** mutate every envelope/manifest/provenance
  field and prove incomplete or contradictory evidence cannot pass.
- **R5-G16 / deterministic harness:** replay each reference schedule twice
  across environment permutations and compare normalized canonical evidence.
- **R5-G17 / convergence:** verify exact DAG closure, phase receipt identity,
  gate non-regression, cross-phase suite, and rollback-edge coverage.

## Phase-gate algorithm

For PG0 through PG5, the verifier:

1. resolves the exact phase requirement set from the hashed DAG;
2. verifies every requirement-gate receipt against its independent trust anchor;
3. verifies predecessor phase receipts and candidate ancestry/tree bindings;
4. rejects extra runtime scope not declared for the phase;
5. runs the phase composition fixtures and rollback matrix;
6. emits one signed, immutable phase receipt without merge/deploy authority.

Any missing prerequisite, graph cycle, stale tree, scope excess, skipped fixture,
or unverifiable artifact yields `EVIDENCE_INCOMPLETE`. An observed invariant
violation yields `FAIL`. No automatic retry may overwrite either result.

