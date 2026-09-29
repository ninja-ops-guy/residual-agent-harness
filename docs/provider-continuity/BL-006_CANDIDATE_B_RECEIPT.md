# BL-006 — MODEL ADMISSION PREFLIGHT — CANDIDATE B RECEIPT
**Author:** Mason (LEGION, b_swjen7ya26ehj2b) · **Date:** 2026-09-28
**Authority:** Piston's Candidate A adjudication (receipt `cff9f950…`) + owner dispatch 2026-09-28T05:51Z
**Base:** Candidate A bytes preserved (Hermes, digests `c36c7819…` / `aac0db33…` / `075a89ce…`)
**Target:** `MODEL_ADMISSION_PREFLIGHT_QUALIFIED`
**Isolation:** No provider calls, no model loads, FreeLLMAPI runtime untouched.

---

## Candidate A preservation

Candidate A is frozen, not overwritten. Source directory `/root/.openclaw/workspace-main/main/bl-006-successor-candidate/` untouched. Candidate B works from a copy.

## Corrections landed (Piston receipt cff9f950…)

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| F1 | HIGH | TTL never enforced at consume — expired admissions consume successfully | `consume()` now checks `expires_at` against current time; expired → refuse `admission_expired`, fail-closed. Exact-boundary test: `ttl_minutes=0` envelope refuses. |
| F2 | MODERATE | Receipt claims §9.2 M6a MEASURED_DERIVED lookup implemented — no lookup function exists | `lookup_measured_profile()` implemented: exact-key MEASURED → nearest-bucket MEASURED_DERIVED (bucket_delta recorded) → None/CLAIMED. |
| F3 | LOW | Hardcoded `/root/.openclaw/…` sys.path in test file | Removed; replaced with `os.path.dirname(os.path.abspath(__file__))`. |
| M5 | — | Consume-time manifest version check required for QUALIFIED | `consume()` accepts optional `manifest_row_digest`; mismatch → refuse `manifest_version_mismatch`. |

## Verification battery: 45/45 GREEN

| # | Test | Result |
|---|------|--------|
| 1–14 | Candidate A battery (unchanged) | 34 GREEN |
| 15 | F1: TTL enforcement — expired-at-creation refuses `admission_expired` | GREEN |
| 16 | F2: M6a lookup — exact MEASURED, nearest MEASURED_DERIVED (Δ=4096), absent CLAIMED | GREEN |
| 17 | M5: manifest version check — correct digest consumes, wrong digest refuses | GREEN |

Two consecutive runs, deterministic. Zero network I/O. Zero provider calls.

## New artifact digests

| File | SHA-256 | Bytes |
|------|---------|-------|
| `admission.py` | `33f92efe8f2fac50f3038ba2d566abaaf97bebed163d0d14345461d47e3b2f8c` | 22,766 |
| `test_admission.py` | `ba7ac6a2d98f413452a892922fb6282ab8e038ecb8b35b69417f853bc1c12bb3` | 20,727 |
| `BL-006_CANDIDATE_B_RECEIPT.md` | `c8784c4411306245f3b8f7befe930072ea81aaeed4d15933ef50da7fd938e1a4` | 3,388 |

## Isolation attestation

- No provider calls: pure Python + SQLite; zero network I/O.
- No model loads: no runtime adapter invoked.
- FreeLLMAPI runtime untouched: no HTTP requests to `:3001`.
- Candidate A untouched: source directory read-only for this lane.
- Ghost's failed path untouched: no ollama auth config read or modified.

## Known limitations (B-class)

1. Manifest registry still in-memory dataclass; persistent registry is future work.
2. Load gate (runtime adapter digest re-derivation) specified but not exercised — no live runtime.
3. Reaper (30-day evaluation reap) specified but not scheduled.
4. UI projection (§10) interface boundary only.

## Next

Self-verifying transport → Piston complete fresh qualification battery → `MODEL_ADMISSION_PREFLIGHT_QUALIFIED` or first failure.

*Mason — LEGION seat · BL-006 Candidate B · filed 2026-09-28*
