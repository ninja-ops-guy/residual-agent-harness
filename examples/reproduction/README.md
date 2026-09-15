# Synthetic offline bundle

Run from the repository root:

```bash
python -m residual.reproduce synthetic-demo --runs-dir examples/reproduction
```

All data and model/Git identities are fabricated. Six scheduled cells deliberately
include an incorrect acceptance, UNKNOWN grading, a timeout, and a missing outcome.
No provider is configured or called. This fixture is outside any confirmatory study.

See `docs/program/reproduction/README.md` and `bundle-v1.md` for the contract,
metrics, provenance limits, and remaining science integration gates. Do not edit
retained files without issuing a new bundle/manifest; tests copy this fixture into
a temporary directory before tampering with it.
