# Status Documentation

RESIDUAL currently has two status views:

- [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) — generated from `implementation-status.yaml` by `scripts/status_check.py`.
- [`CURRENT-MAIN.md`](CURRENT-MAIN.md) — short human-readable snapshot for newly merged work that may not yet be reflected in the generated manifest.

The generated file remains the long-term structured source for requirement-family status. `CURRENT-MAIN.md` exists to prevent fast merge waves from making top-level documentation obviously stale between manifest regeneration passes.

For exact current behavior, source and tests win over prose.