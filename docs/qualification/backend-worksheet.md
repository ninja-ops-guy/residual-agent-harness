# Backend Determinism Qualification Worksheet (blank)

Status: blank template. Complete one worksheet per (backend, target class). Attach
evidence bundles by hash; never edit or delete a submitted worksheet — append an
amendment referencing the predecessor bundle/entry instead.

```
Backend determinism qualification worksheet — v1
=================================================
Backend ID: ____________________   Kind: [ ] llm_adapter [ ] browser_provider
           [ ] sandbox_executor  [ ] fixture_harness [ ] in_process_executor [ ] other
Backend version: ________________  Commit: __________________  Tree: __________________
Platform(s): ________________________________________________

Target class:  [ ] D1  [ ] D2  [ ] D3  [ ] D4
Current class (from ledger): ____   Status: [ ] HELD  [ ] DEGRADED  [ ] REOPENED

Suite:  id ____________  version ________  seed ______  input hashes attached: [ ]
Excluded-from-comparison fields (timestamps/UUIDs/entropy): ______________________

Evidence bundles (append-only; list all, newest last):
  # | bundle_id | date | class_attempted | result | commit | bundle sha256
  1 |           |      |                 |        |        |
  2 |           |      |                 |        |        |

Entry-evidence checklist for target class:
  [ ] 3+ repeat runs, same commit/tree/platform (D1)
  [ ] equivalence relation declared; pairwise comparison PASS
  [ ] seed recorded; replayed >= 2x, canonical-bitwise equal (D2)
  [ ] >= 2 distinct (platform, machine) environments; restart/replay run (D3)
  [ ] network-disabled replay run; negative control tamper detected (D4)
  [ ] envelope: skip_count = 0, unknown_count = 0, tracked_source_dirty = false
  [ ] envelope.source commit/tree are full 40-hex git object ids
  [ ] validator PASS: python scripts/qualification_determinism.py <bundle.json>
  [ ] non_claims enumerated (what this evidence does NOT establish):
      ________________________________________________________________

Requalification triggers since last qualification (from determinism-classes.md §4):
  ________________________________________________________________

Amendments/reopenings linked (predecessor bundle ids):
  ________________________________________________________________

Assessor: ____________  Date: ____________  Ledger entry id: ____________
```

Notes:

- `UNKNOWN` and `SKIP` outcomes are recorded as observations and never count
  toward class entry; missing capability or credentials yields `UNKNOWN`.
- A worksheet claiming D3/D4 without the restart, environment-matrix,
  air-gapped replay, or negative-control evidence is invalid on its face.
