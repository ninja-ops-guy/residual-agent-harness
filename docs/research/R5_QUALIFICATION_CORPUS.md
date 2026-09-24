# R5 Shared Comms qualification corpus

Status: qualification/test infrastructure only. This document and its
machine-readable companion do not implement R5 runtime behavior.

Authority is PR #410 and frozen R4.1 candidate
`8701367db6d3202f24b3eb9f4696b0cadf657985` (tree
`79bfe6ed1743907065ed44aeb9c460c47527e0c6`). The candidate was not modified.

`tests/qualification/fixtures/r5_shared_comms_corpus.json` supplies, for every
R5-SC-001..014 requirement, a positive, negative, and adversarial fixture
description; the invariant; required evidence; a deterministic oracle; and
false-positive/false-negative risks. `test_r5_shared_comms_corpus.py` fails if
any requirement, gate, or required field disappears.

## Gate implementation contract

Each future gate runner should consume one frozen corpus row and emit:

1. candidate and harness HEAD/tree plus corpus SHA-256;
2. fixture IDs and deterministic fault-point schedule;
3. raw evidence named by the row, never only a derived summary;
4. the expected invariant and an independently computed oracle result;
5. `PASS`, `FAIL`, or `BLOCKED` (missing/skipped/malformed evidence is not
   `PASS`); and
6. retained counterexamples for every failure.

The prioritized first tranche is R5-G01..G05: concurrent recovery fencing,
cryptographically request-bound receipts, explicit indeterminate state,
malformed/cross-bound receipt rejection, and crash-safe ACK persistence. Final
qualification must exercise real process, SQLite, filesystem, and receiver
boundaries; in-memory doubles are suitable only for corpus/unit prechecks.

## Known oracle traps

- A receiver's idempotency count is not an oracle for sender ownership.
- A signature over mutated content is not a negative receipt-binding fixture.
- Reading the same derived metric under test is not independent recomputation.
- A process kill that misses the named WAL/fsync boundary is not fault evidence.
- Safe loss of liveness is not a safety violation.
- Duplicate delivery is not duplicate external effect when the declared effect
  ledger proves stable-ID deduplication; the claim boundary must remain explicit.

## Safety and disposition

Evidence source: PR #410, R4.1 Seal v2, and authoritative R4-G10/G13/G14
records. Scope: post-canary R5 qualification planning. Blockers: runtime gates
do not exist yet. Pre-canary finding: none asserted by this corpus alone.
Pre-production finding: R5-G01..G11 require qualification before broader
production use. Research findings require ablation and literature review.
Canary execution status: **NOT EXECUTED**.
