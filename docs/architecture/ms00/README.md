# MS-00 run ledger — design artifacts

- `../MS-00-run-ledger.md` — the design document (schema, transition API, CAS SQL,
  crash matrix, migration, implementation plan).
- `reference_ledger.py` — minimal dependency-free SQLite reference implementation.
  Design artifact only; not the production MS-00.
- `tests/test_ms00_contract.py` — pytest contract skeletons encoding the normative
  semantics (I-1..I-6, crash matrix KP rows). Green against the reference; binding to
  the future production implementation is a one-fixture change (`ledger_factory`).

Run locally (no repo dependencies):

```
python3 -m pytest docs/architecture/ms00/tests/test_ms00_contract.py -q
```

Verified at authoring: 17 passed (3 consecutive runs), Python 3.11+, pytest 9.1.1.
