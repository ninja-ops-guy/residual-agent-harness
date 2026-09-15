# M4 hosted candidate evidence — 2026-09-15

PR #109 head: `91c9ae671cea9dea761b67dc1b462c62569c0b2d`.
Accepted main parent: `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9` (#121 squash).
Tested synthetic merge: `dd27daa6672bff975e714d735eb05d1a5d8a2a9a`.
Both candidate and synthetic merge have tree `3924c1de206789d78296fddfaeb7085d24ef5862`;
this equality was checked through Git commit records.

[M4 workflow 35008093028](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35008093028)
and job 104512834093 succeeded on Ubuntu 22.04 image `20260907.292.1`.
The retained decoded job log records actual isolated execution, overall PASS,
and **135 tests plus 78 subtests passed**, followed by a successful zero-skips assertion.
No host-policy relaxation or skip waiver was added. This is candidate evidence,
not qualification of a future RC or an elapsed soak.

## Retention and verification limits

`job.log` is the decoded GitHub job log retrieved through the connector.
`artifact-metadata.json` retains GitHub's artifact identity, expiry and reported
SHA-256. Artifact 10412223138 expires on 2026-09-29. The artifact download
returned HTTP 403 locally: **the ZIP was not independently downloaded, hashed,
or inspected**. The reported digest is not a locally verified archive digest.
Download and retain the complete artifact before expiry, then inspect its
source/environment record, report and JUnit before independent acceptance.
`SHA256SUMS` verifies only the retained files in this directory.

## Remaining merge blockers

- Fresh independent review of #109, including the earlier prerequisite repair
  and the workflow's temporary runner selection, remains outstanding.
- Broader [CI run 35008092614](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/35008092614)
  failed on Python 3.13: `LifecycleGuards.test_missing_cli_input_returns_sanitized_blocked_json_for_both_run_aliases`,
  `--trace-id` subtest, raises JSONDecodeError while parsing stderr at line 139.
  Its raw decoded log is retained as `ci-failure.log`: 1005 tests, one error,
  22 skips. Sibling matrix jobs were cancelled. Root cause is not established;
  passing M4 tests do not waive this failure.
- At the latest observation, a demo browser-proof check was still running.

#121 merged as `1a52e9a2`; all 13 listed checks on that main commit succeeded.
#109 remains unmerged. This continuation implemented its repair and cannot
provide independent approval. Runtime/recovery, 72-hour soak, blank-machine RC,
the final demo and ER1 remain separate acceptance gates.
