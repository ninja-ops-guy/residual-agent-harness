# Verifier Index

## v1 — 2026-09-14
- Script: `verifier/v1/check_specs.py`
- Measures: (1) all 17 harness_specs files present; (2) no
  TODO/TBD/FIXME/placeholder markers; (3) PATH_TO_10 N9-R1..28 and
  T10-R1..20 contiguous; (4) every requirement family contiguous from
  R1; (5) RFC 2119 declaration in every normative doc.
- Result: FAIL — DESIGN.md lacks an RFC 2119 declaration.

## v2 — 2026-09-14
- Script: `verifier/v2/check_specs.py`
- Differs from v1: DESIGN.md reclassified as non-normative (it is a
  design-rationale document, contains no RFC 2119 requirements).
- Result: PASS — 17/17 files, N9=28, T10=20, all families contiguous.
