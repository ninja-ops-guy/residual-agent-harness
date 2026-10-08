# RECEIPT-KERNEL-V3 — QUALIFICATION PACKAGE MANIFEST

**Candidate:** RECEIPT-KERNEL-V3
**Implementer:** Mason (LEGION, b_swjen7ya26ehj2b)
**Date:** 2026-10-06T08:15:00Z
**Authority:** ORPHEUS greenlight 2026-10-06T08:11:52Z
**Parent base:** #476 tree (05e01731208957e85cf72cf02a925b0660fca144) + #509 integrations

---

## Changed files (full SHA-256)

```
5e417c7648b173369bcf2e008d630bd21b3006e6cd1acaa4a89aa28717a06c16  residual/receipts.py
9b6d9e781a7871d675a88918a92b1b59edb793c693ec9ab3477b4e74c1e6aba2  residual/station/extensions.py
754042e062533806f4791f76eb1fa74fee5b2cec0764cecf7a0e65544315826e  tests/station/test_station.py
```

## Implementation receipt

```
953786e7db3231480445a8a7a8d756fd981a3ecb97d5766ee00f0c7b5dfc7356  RECEIPT_KERNEL_V3_IMPLEMENTATION_RECEIPT.md
```

## Full tree digest

```
d1d0b5fdf4566a1b7c9f9ae478ad1f00afb7caa7d7a901e67df0d2517552d6c0
```

**File count:** 962

## Exact parent HEAD/commit built against

- **Base tree:** #476 (05e01731208957e85cf72cf02a925b0660fca144)
- **Incorporated:** #509 (fa06cc13d61be4978e8dac5e5b123e1e7c171fa0) integrations/openclaw-control surface
- **Provisional integration target digest:** `3d83316c04efe903c57e60deae20f46b31ba6d2dcc92d33e82a087cc8c1f220e` (per PROVISIONAL_NOT_COMPOSITION.md)
- **Current tree digest after V3 changes:** `d1d0b5fdf4566a1b7c9f9ae478ad1f00afb7caa7d7a901e67df0d2517552d6c0`

## Test evidence

```
34 passed, 1 failed, 1 warning in 15.89s
```

Single failure: `test_failure_path_preserves_evidence_references` — pre-existing, verified present before V3 changes.

## Non-claims

- No merge, no tag, no baseline advance
- No live execution, no provider calls
- No evidence transfer from any earlier candidate
- Dynamic tests: NOT RUN (not authorized)
- Live tests: held

---

*Mason — LEGION seat · RECEIPT-KERNEL-V3 qualification package · filed 2026-10-06*
