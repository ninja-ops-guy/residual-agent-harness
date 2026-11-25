# Shared memory implementation evidence

Candidate base: accepted main
`8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`.

The implementation and source hashes are recorded in `validation.json`.
`station-tests.log` contains the complete local Station run: **68 tests passed**,
including **31 new shared-memory tests**. The existing 37 tests retain their
budget, receipt, reviewer, lease, state, remote submission and integration checks.
The installed Python runtime lacked pytest; these unittest suites were executed
with their native standard-library runner, not marked untested or skipped.

`recovery-demo.json` records a separate offline end-to-end example with real
SQLite, Git worktrees, subprocess restart, acceptance checks and the existing
scripted-demo reviewer. A replacement worker inherited the exact earlier failed
evidence, the departed worker's lease was rejected, and the corrected task passed
fresh review/integration while its earlier failure remained available. The demo
used zero providers. Its generated event/commit IDs identify temporary fixture
state, not real user work or a retained production database.

Run the [documented commands](../../docs/station/SHARED_MEMORY.md) to reproduce the
behavior. Hashes bind the actual inspected source bytes and logs. They do not
provide independent-human assurance or prove correctness outside the checks.

Root review identified narrower commit-ID validation, repeated-artifact read
amplification, review-consistency validation and malformed-projection exception
handling. The final source includes the corresponding corrections and behavioral
regressions. No workflow, licensing boundary, protected pin, current-main state,
live service, host or external agent was modified.

This is an isolated local implementation result. It is not DBOX/LEGION/native
SC-MESH qualification, full-repository CI, a P5 after-condition, measured operator
effort reduction, a release approval, or evidence of 24-hour production recovery.

`independent-review.json` and `independent-tests.log` retain the root agent's
separate rerun of all 31 new tests, with stable before/after source hashes. This
is independent agent execution and review within the same scratch environment,
not independent human assurance or a second physical host.
