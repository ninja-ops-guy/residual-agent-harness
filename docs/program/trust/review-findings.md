# Findings against the pinned PR #81 revision

Target: `30d1d020469d958d90969bc02946145c248e0adb`.
This review does not edit that branch and does not close #63.

| Finding | Severity / confidence | Evidence and impact | Required disposition |
|---|---|---|---|
| TRUST-001: candidate retains namespace privileges after setup | High-priority trust review; **source-level concern, not a demonstrated escape** | `_isolated_child.py` creates a read-only bind, calls `PR_SET_NO_NEW_PRIVS`, and execs candidate code without an explicit capability drop. No-new-privileges does not itself remove currently held capabilities. A candidate may be able to remount its candidate bind writable, change the bytes a verifier observes and restore them before the host's post-check snapshot. | Execute bounded `readonly_bind_remount` probe on capable Linux; review/remedy capability lifecycle and add transient-mutation integration regression. Our host denied namespace creation, so it provides no evidence either way. |
| TRUST-002: malformed Git size escapes typed evidence | Reproduced; failure-semantics gap | `read_base_blob()` parses `int(size_raw)` outside a handler for `ValueError`; scripted successful `cat-file -s` returning `not-a-size` raises a raw exception instead of returning ERROR. This does not demonstrate acceptance of corrupt Git content. | Validate finite nonnegative size and catch malformed response as typed ERROR; remove strict expected failure after review. |
| TRUST-003: string `false` becomes a met requirement | Reproduced; input validation gap | `VerificationDecision` transforms requirement values with `bool(v)`. A string `"false"` becomes `True`. The test demonstrates the constructor coercion; it does not assert an untrusted worker can reach Station issuance with a forged decision. | Reject non-boolean requirement values at the authoritative boundary, then test the complete issuer path. |
| TRUST-004: NaN scheduler threshold accepted | Reproduced; configuration validation gap | `SchedulerPolicy(imbalance_ratio=float('nan'))` is accepted. Both greater-than and less-than comparisons with NaN are false, so the normal imbalance controls can be silently disabled. | Require a finite numeric threshold (excluding booleans), with explicit malformed-configuration evidence. |

The three reproduced failures are marked `xfail(strict=True)` so tests preserve
the desired behavior without pretending the implementation currently has it.
The preflight runner reports them as `KNOWN_GAP` and exits 2 even though pytest
itself regards expected failures as a successful test session. Fixes produce a
strict unexpected-pass failure until the test annotation is reviewed/removed.

## Additional reviewed limitations

- The sandbox uses per-process address-space/CPU limits and an advisory NPROC
  limit, not a demonstrated aggregate cgroup memory/PID budget. The bounded
  eight-child probe tests basic process operation only. It does not establish
  fork-bomb resistance or a whole-tree resource ceiling.
- The sandbox's exit-125 plus stderr-prefix convention can be imitated by
  candidate code. That may change failure classification to launch UNKNOWN;
  it is not an acceptance bypass. Provenance should eventually use an
  unforgeable bootstrap channel rather than candidate-controlled stderr.
- The retained run has no executed namespace probe payloads. A denied
  prerequisite is not a denied attack and is not evidence of containment.
- The property tests focus on byte identity, ordinary Git object framing,
  bounded malformed inputs and deterministic transitions. They are not an
  exhaustive sandbox or cryptographic audit.
