# Independent trust preflight

This lane owns additive tests and evidence only. It does not alter PR #81,
runtime code, accepted state, issue #63, or the confirmatory model study.

The reviewed target is PR #81 commit
`30d1d020469d958d90969bc02946145c248e0adb`, tree
`496cd8257bb06eaf71e69b3e730398032082cba4`. The implementation branch for this
lane starts at main `dec571992a97b4ae80f0310aa32ffd8f542aef8c`.

## Run against a separate pinned checkout

Install the ordinary Factory dependencies, pytest and optional Hypothesis in
your test environment. Hypothesis is deliberately not a runtime dependency.

```sh
git worktree add --detach ../residual-pr81 30d1d020469d958d90969bc02946145c248e0adb
python scripts/run_trust_preflight.py \
  --target ../residual-pr81 \
  --expected-commit 30d1d020469d958d90969bc02946145c248e0adb \
  --output ../trust-evidence-pr81 \
  --sandbox
```

Use a fresh empty output directory outside a clean detached target checkout.
The runner rejects untracked and ignored files (including Python caches), uses
a controlled subprocess environment, and ignores inherited PYTHONPATH. Supply
`--dependency-path /absolute/path` for an explicit optional dependency directory.
The runner verifies the
actual imported package path, records target commit/tree, exact commands,
platform/Python/dependency versions, hashes of test sources and output logs,
JUnit outcomes and a complete source-file/directory inventory. It checks that
the target input inventory remains unchanged. The whole pytest process group
has a 300-second default deadline (`--timeout-s`, maximum 900); timeout retains
logs and reports INCOMPLETE, never a pass.

Exit codes: **0** means the selected executable suite has no failing or missing
checks; **1** means a test/tooling failure; **2** means incomplete coverage,
including skips or known defects marked strict `xfail`. Even exit 0 would not
implement the missing invariants in [architecture-invariants.md](architecture-invariants.md).
It is not permission to close #63 or execute the confirmatory study.

## Scope of executable checks

| Mechanism | Independent oracle | Bound / limitation |
|---|---|---|
| Canonical artifact paths | Path components round-trip exactly; aliases rejected | 60 generated examples/property, four components |
| Snapshot identity | Independent SHA-256, creation-order equivalence, content/mode sensitivity | Eight files, 256 bytes/file; directories remain observable |
| Receipt serialization | JSON/key-order round-trip; metadata mutation invalidates retained hash | Signed evidence authentication is exercised separately in the integration fixture |
| Git classification | Scripted Git I/O responses, independently computed blob OID | Does not emulate every Git corruption mode |
| Scheduler transitions | Generated transition sequences retain plan hash and capacity bounds | 20 transitions/example; no distributed leases |
| Accepted Git tree | Real Git, EvidenceBus, Station signature, exact path set and byte oracle | Ten generated integrations; reviewed no-op verifier fixtures, **not isolated verification** |
| Filesystem TOCTOU | Deterministic symlink replacement after inode validation | Injected leaf replacement is asserted; no probabilistic claim about all races |
| Failure attribution | Timeout, signal, output cap and launch failures cannot support candidate attribution | Pure policy tests |
| Sandbox | 13 bounded authored probes with exact execution-marker hashes | Real namespace boundary required; never unsandboxed fallback |

The accepted-tree property reuses the pinned repository's integration setup
helper to assemble contracts/receipts. It independently derives the expected
Git byte inventory. This is independent assertion coverage, not a completely
independent implementation of the production pipeline.

Hypothesis tests use deterministic generation, no example database, 60 examples
per property except the ten real Git integrations. Each example creates and
cleans up its own mutable files/objects. Only the stateless API loader is a
session fixture. Hypothesis absence skips its module explicitly; missing PR #81
APIs skip individual tests without blocking collection of compatible tests.

## Qualification status

The retained run is **INCOMPLETE**: local namespace creation is unavailable,
so no sandbox attack was attempted. Three strict expected failures document
reproduced validation gaps. See [review-findings.md](review-findings.md) and the
machine-readable evidence under `evidence/`.

Before trust qualification: resolve or explicitly disposition each finding,
execute the probe suite on a disposable Linux host that supports the real
namespace profile, review every UNKNOWN and unexpected pass, and re-run on the
actual merged-main commit/tree. No model calls are needed for this lane.
