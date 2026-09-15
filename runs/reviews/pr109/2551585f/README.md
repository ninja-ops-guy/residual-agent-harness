# PR #109 repair and acceptance handoff

Candidate: `2551585f8951d242db92cd4c3e680409b0e4c572`.
Tree: `0299afd8e0caef5cc247317b5ed2d41423f86a14`.
Accepted base: `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9`.

## Delivered and verified

- Package CLI `python -m residual.factory` invokes existing runtime main after
  package initialization. The prior direct runtime module command emits a
  reproducible runpy warning; no warning filter was added.
- Both run-ID aliases are checked in real subprocesses. All original exit,
  stdout, exact JSON, path-sanitization and empty-journal assertions remain.
- Parent-warning injection passes for both aliases. Reverting global stderr
  capture reproduces JSONDecodeError; `cli-capture-mutant.log` retains the failure.
- Local 21 unittest cases and 21 pytest cases plus 22 subtests pass.
- [Fresh M4 run 35010813043](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35010813043)
  passes 135 tests plus 78 subtests with zero skips. Its exact ZIP, extracted
  members, GitHub digest and source-commit record are retained in
  [the M4 bundle](../../../qualification/m4/2551585f/README.md).

## CI and remaining gate

Ordinary CI remains **RED**, correctly: the protected lifecycle test's blob
differs from its existing ownership pin. The retained Python 3.11 and 3.12
full unittest logs each report 1006 cases with one failure, the unchanged
ownership assertion, and 22 namespace skips. Other observed qualification
failures also name that mismatch. Matrix siblings were cancelled; no full
Python 3.13 or full-pytest PASS is claimed for this candidate.

Old protected blob: `d4e00bd290351fa2ccd302ac578ac5dc463eda84`.
Proposed protected blob: `85c6bf10a675ea3a74d775906d0bbaa79e411100`.
The other 37 protected files and the baseline are byte-unchanged.

The required next step is independent review of the protected test, the CLI
entry point, the warning-injection mutation result, and the prerequisite /
evidence-export changes in #109. Only after approval may the ownership
baseline be deliberately advanced and fresh CI/qualification completed.
This implementer has not self-approved, changed pins, or merged #109.

## Historical-cause limit

The two failures at `91c9ae67` did not retain the rejected JSON document.
The instrumented suite at `1e4c02c5` subsequently passed, so the historical
warning's exact origin remains unknown. The retained fault injection proves
the old capture's sensitivity, not the source of that historical warning.
SQLite ResourceWarnings elsewhere in those logs remain resource-lifetime
findings; this patch does not claim to repair all connection leaks.
