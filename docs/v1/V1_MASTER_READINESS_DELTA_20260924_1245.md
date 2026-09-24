# RESIDUAL v1 master readiness delta — 2026-09-24 12:45 UTC

This append-only correction supersedes only the #440 head identity recorded in the immediately preceding delta. It does not authorize execution or alter any frozen evidence.

Accepted main remains `d796f36b75e730a0bab71bdba564206174393719`.

## PR-G27 remediation exact-head correction

Draft PR #440 remains the concrete immutable GitHub Actions remediation candidate, but its current exact head is now:

`786b8978256d2dff6442a45ec87c5443cc097c65`

The prior `ecb598456637ea9b474c31f76c474dd7c071aa7c` head is superseded and its checks must not be inherited.

Reason for the head advance: a manual re-read of the compatibility change in `tests/test_pages_main_qualification_gate.py` found an incorrectly double-escaped regex boundary. The current head fixes the test to require an immutable 40-hex `actions/deploy-pages@` ref with a real regex word boundary. This is a test-correctness repair, not a weakening of the Pages gate.

A changed-workflow diff inspection on the remediation proposal found no added external `uses:` reference with a mutable ref. The candidate continues to pin the eight previously floating GitHub Actions families and retain the already immutable PR-Agent action.

Exact-head GitHub Actions for `786b897...` are currently queued/running. Therefore PR-G27 and #440 remain `IN_PROGRESS`, not `READY_FOR_REVIEW`.

All previously stated canary, deployment-profile, AUD-1/physical, RC recovery/rollback/soak, and release-authority blockers remain unchanged.
