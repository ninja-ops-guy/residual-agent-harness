# AUD-1 post-review execution packet

Status: **HELPER RECONCILIATION PREPARED — PHYSICAL F6 NOT EXECUTED**

This packet belongs to the AUD-1 implementation lane. It does not replace the v1
Release Convergence master checklist, shipping documentation, canary procedures,
or release authorization.

Selected software candidate for helper reconciliation:

`#448 @ 7001bdf68355b7e5288a8cea3f4c827061aca37d`

Current frozen physical helper:

`#403 @ 118ec3c795ae11c88b68278717fb781f4b059559`, still bound to
`#399 @ 8df77b832b3839ccd2a6944a65760ce3ab10dc9c`.

The exact candidate was selected by the owner record on #448. This document
authorizes no physical test, owner attestation, merge, or release action.

## Gate 0 — independent human technical review

Required before candidate selection:

- retained historical review target: #438 head
  `e815f33484352f100e11b8d075bb954a815244cc` (evidence only; not executable);
- explicitly cover C1-C6;
- explicitly assess the completion-barrier policy:
  - admitted work drains rather than being preempted;
  - new work is writer-fenced while a control change is pending;
  - C6 bounds the control wait with a monotonic 600-second deadline;
  - timeout occurs before credential/access mutation and returns 503;
  - timeout releases writer-pending state and does not falsely report revocation;
- return one of: `ACCEPT`, `ACCEPT WITH FOLLOW-UP`, or `CHANGES REQUIRED`;
- bind the review to the exact commit SHA.

PR-Agent output is advisory and is not this gate.

## Gate 1 — explicit candidate selection

Only after Gate 0 is acceptable, the owner records one exact selected AUD-1
candidate SHA. Selection must be a separate decision from review and must not be
inferred from CI green status.

Before any helper work, re-read:

- selected candidate head;
- #403 exact head;
- issue #353;
- current helper source and tests;
- selected-candidate qualification evidence.

If any head moved, stop and reconcile before writing.

## Gate 2 — helper reconciliation and qualification

Do **not** rewrite frozen #403.

Start a new helper successor from exact frozen #403 head
`118ec3c795ae11c88b68278717fb781f4b059559`.

Before editing, run the read-only preflight from this preparation branch against
two clean checkouts:

```text
python tools/aud1/helper_retarget_preflight.py \
  --helper-repo <exact-clean-successor-checkout> \
  --candidate-repo <exact-clean-selected-candidate-checkout> \
  --expected-helper-head <exact-successor-40-char-SHA>
```

For this selected successor, the expected validation status is `PASS`. It means
only that helper reconciliation is coherent; it does not authorize physical F6.

After explicit selection, the helper successor must atomically reconcile every
candidate binding, including at minimum:

1. `tools/aud1/f6_collect.py::TARGET_SHA`;
2. `tools/aud1/Run-F6-Physical.ps1::$Target`;
3. `tools/aud1/f6_bound_station.py::TARGET_SHA`;
4. `tools/aud1/README.md` and `tools/aud1/STRICT-PHYSICAL-GATE.md`.

The preflight also performs a closed-world scan over `tools/aud1` and
`tests/tools`; any literal frozen target SHA in an unaccounted file is a refusal,
not an implicit extra retarget.

Retain without weakening:

- exact candidate SHA and clean-worktree refusal;
- Station process candidate-head/repository/module provenance checks;
- remote-runner process/TCP evidence requirements;
- distinct F6-A and F6-B evidence bundles;
- F6-B old-runner surrender evidence;
- reassignment to a different live runner;
- stale-result probe bound to original project/task/lease and the expected
  reassigned-authority HTTP 403 denial;
- redaction;
- closed-world manifest freeze and tamper verification.

Run fresh exact-head CI on the reconciled helper. No prior #403 CI transfers to
the successor.

## Gate 3 — F6-A real-host evidence

Requires distinct owner authorization for physical execution.

Case: interruption and restoration **inside** the worker authority/grace window.

Required retained observations include:

- selected candidate exact head and clean checkout;
- Station process provenance bound to that checkout;
- old runner owns the task before interruption;
- transport is demonstrably down;
- restoration occurs inside the permitted window;
- same valid authority continues without duplicate owner/invalid transition;
- terminal state is captured;
- evidence bundle freezes and verifies.

A CI fixture is not F6-A.

## Gate 4 — F6-B real-host evidence

Requires separate retained evidence from F6-A.

Case: interruption beyond the worker authority window, natural expiry/recovery,
reassignment, then old-runner return.

Required observations include:

- old runner initially owns the task;
- transport remains down beyond the authority window;
- old worker records authority surrender;
- server-side recovery/reassignment is not manufactured by DB editing;
- a different valid runner owns the recovered task;
- old transport returns only after reassignment;
- explicit stale result using the old project/task/lease receives the required
  reassigned-authority HTTP 403 denial;
- no stale result is accepted;
- evidence bundle freezes and verifies.

The 180-second worker grace and 900-second server lease are not shortened to
manufacture evidence.

## Gate 5 — Mason/LEGION independent read-only re-audit

Provide the packet in `docs/security/AUD1_MASON_REAUDIT_PACKET.md` plus the
selected candidate diff, exact-head qualification artifact, and the two physical
F6 bundles.

Unavailable physical evidence stays `PENDING`, never inferred from CI.

## Gate 6 — owner attestation and integration handoff

Only after independent review, helper qualification, F6-A, F6-B, and the
independent re-audit are acceptable:

- run fresh selected-head qualification if bytes changed;
- obtain genuine owner attestation bound to exact SHA;
- hand the selected exact SHA and expected-head integration condition to Release
  Convergence;
- do not auto-merge or push directly to main from this lane.

Resulting-main push qualification/Pages, shipping reconciliation, RC artifact
verification, clean-environment recovery, elapsed soak, and final release
authorization remain owned by their existing release gates.
