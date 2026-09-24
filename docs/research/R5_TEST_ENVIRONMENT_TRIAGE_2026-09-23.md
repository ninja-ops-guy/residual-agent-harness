# R5 planning-lane broad-suite environment triage

Target/base: `91d32fd8b713c68c1cd2e473013c9e1c33b93572` (tree
`6b54a3d1086a4e132b6c5476311fae48facaa5b5`). No product code changed.

## Reproducibility matrix

| Run | Command / environment | Tests | Failures | Errors | Skips | Interpretation |
|---|---|---:|---:|---:|---:|---|
| PR #410 reported | exact command not retained in PR body; restricted planning environment | 1121 | 5 | 95 | 29 | environment-limited, not a regression verdict |
| independent rerun A | `python -m unittest discover -v`; same Git tree; restricted environment | 1146 | 5 | 96 | 30 | same failure shape; expanded discovery/count remains unexplained |
| independent rerun B | `python -m unittest discover -s tests`; same tree/environment | 1146 | 5 | 96 | 30 | start directory does not explain the 25-test delta |

The exact 1121 count is not reproducible without the original command,
interpreter/module inventory, environment variables, and discovery log. The
same Git tree rules out a stale source base as the only explanation; discovery
or environment-dependent loading remains an open hypothesis.

## Failure classification

| Class | Evidence | Classification | Required confirmation |
|---|---|---|---|
| loopback server creation | repeated `ThreadingHTTPServer(('127.0.0.1', 0), ...)` fails at `socket()` with `PermissionError: [Errno 1] Operation not permitted` | environment/setup failure; dominates errors | rerun where AF_INET loopback bind is permitted |
| Ed25519 support | `cryptography` is absent; `StationIdentity.generate()` raises `EvidenceError("cryptography Ed25519 support is required")` | missing optional dependency (`factory` extra), not product regression | install the declared `.[factory,qualification]` environment and rerun |
| sandbox runtime | `bwrap` 0.6.1 is installed, but its namespace preflight fails `Creating new namespace failed: Operation not permitted` | environment capability failure | runner permitting the exact workflow bwrap preflight |
| five assertion failures | four report candidate/runtime failure code 122 before the intended SQLite/watchdog path; one injection never reaches the lease-read path | downstream of unavailable sandbox capability; not established regressions | rerun only after bwrap preflight passes; compare exact-head CI |
| skips | count varies 29→30 with environment/discovery; skip reasons were not retained in PR #410 | indeterminate/environment-sensitive | machine-readable test report with reason aggregation |
| stale branch/base | both reported and rerun base identity is the same main commit/tree | not supported as cause of current failure shape | preserve source identity in future reports |
| unrelated historical failures | repository docs retain prior environment-specific namespace failures | plausible context, not proof for each current test | compare against last green exact-tree/capability-equivalent run |

No observed item is classified as a deterministic product regression. That is
not a clean bill of health: the environment prevents the affected tests from
reaching their intended boundaries.

## Minimum environment specification

1. CPython 3.11 on Linux, recording exact patch version (the rerun used the
   unusual `3.11.0rc1`, so it is not a reference environment).
2. Install the project with `.[factory,qualification]`; verify at minimum the
   declared exact qualification versions plus `cryptography>=43` and
   `PyYAML>=6` before discovery. `hypothesis` and `coverage` were also absent in
   the rerun environment.
3. Permit AF_INET loopback socket creation, bind to `127.0.0.1:0`, listen,
   connect, and close; no external network is required for these fixtures.
4. Install bubblewrap and require this preflight to pass before Factory tests:
   `bwrap --die-with-parent --new-session --unshare-pid --unshare-net --ro-bind / / -- /bin/true`.
5. Provide writable, executable disposable storage with SQLite WAL, file locks,
   subprocesses, signals, and enough timer precision for bounded timing tests.
6. Record Git HEAD/tree, command, working directory, Python/platform/SQLite/
   OpenSSL versions, dependency inventory, relevant environment variables,
   capability preflights, per-test outcomes, subtest counts, and skip reasons.
7. Treat capability failure as `BLOCKED` for affected lanes rather than running
   onward and counting cascaded assertions as product failures.

## Proposed gate

`ENV-G01 BROAD_SUITE_PREFLIGHT` must prove dependency, loopback, namespace,
subprocess/signal, SQLite-lock, clock, and writable-filesystem capabilities
before the broad suite. Its evidence is independently hashed and bound to the
test report. A missing mandatory capability yields `BLOCKED`; it cannot yield
`PASS` or `PRODUCT_REGRESSION`.

Evidence source: PR #410 report, two independent same-tree reruns, `pyproject.toml`,
and workflow bubblewrap/dependency preflights. Candidate referenced:
`8701367db6d3202f24b3eb9f4696b0cadf657985`; candidate modified: no. Blockers:
capability-equivalent rerun unavailable. Pre-canary findings: none from this broad
suite. Pre-production: adopt ENV-G01 and retain machine-readable results.
Research: test-count drift under environment-dependent discovery remains open.
Canary execution status: **NOT EXECUTED**.
