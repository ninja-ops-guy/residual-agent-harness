# M4 qualification runner prerequisites + capability probes

`residual/factory/m4_qualification_prereq.py` prepares the runner
prerequisites for the M4 qualification gate intended by draft PR #88
("ci: require actual M4 execution before qualification"). It answers, with
typed machine-readable evidence, whether an environment can run the isolated
M4 verifier (`residual/factory/m4_sandbox.py`, profile
`linux-userns-isolated-v1`) at all.

## What it does

* **Per-capability probes** using the same mechanism as the sandbox's own
  fail-closed probe: the `unshare` argv composed by
  `m4_sandbox._unshare_argv`, decomposed per capability so a BLOCKED report
  names the missing piece instead of collapsing to one
  `namespace_probe_failed`. Probed capabilities: Linux/POSIX platform,
  `os.chroot`, `unshare` binary, user namespace (with root mapping, exactly
  as the sandbox enters it), mount, PID (`--fork`), network, IPC, UTS
  namespaces, `--kill-child`, and the composite sandbox profile probe
  (`m4_sandbox.probe_isolation()`).
* **Actual isolated execution smoke** through `m4_sandbox.run_isolated()`:
  require successful setup, exit 0, the expected execution boundary and exact
  stdout/stderr hashes. A successful namespace probe cannot mask a failed
  child setup, timeout, UNKNOWN or unexpected output. The complete typed
  execution result is retained in the `isolated_execution` capability detail.
* **Reproducible environment manifest** (schema
  `m4-qualification-env-manifest-v1`): OS/kernel release, userns sysctls
  (`max_user_namespaces`, `unprivileged_userns_clone`,
  `unprivileged_userns_apparmor_policy`), Python version checked against the
  pinned 3.12, resource limits (RLIMIT_AS/CPU/NOFILE/NPROC), CPU count, and
  dependency version verification (`cryptography`, `PyYAML`).
* **Explicit PASS/BLOCKED report** (schema
  `m4-qualification-prereq-report-v1`): overall `PASS` only when every
  capability passes; any missing capability, wrong Python pin, or missing
  dependency yields `BLOCKED`. CLI exit code 1 on BLOCKED — never a silent
  skip. Reports are bound to a tested revision SHA via `--revision`.

## Usage

```
python -m residual.factory.m4_qualification_prereq \
    --output runs/m4-qualification-prereq/report.json --revision <sha>
```

The workflow `.github/workflows/m4-qualification-prereq.yml` runs the
probes, the probe regression tests, and the M4 sandbox test suite with a
zero-skips requirement (the same skip-rejection check PR #88 introduced).

## Local evidence

The original submission's environment (Linux 5.10.134-18.0.12 lifsea kernel, x86_64, glibc 2.36,
`max_user_namespaces=22829`, `unprivileged_userns_clone=1`, Python 3.12.12,
cryptography 44.0.2, PyYAML 6.0.2) reported **PASS** on every capability,
and the full `tests/test_factory_m4_sandbox.py` suite ran with 0 skips.
Retained under `evidence/m4-qualification-prereq/` and bound to main tip
`eefee6ac005c93278f483e002e38a768920f0fae`. A BLOCKED report (e.g. a runner
where `unprivileged_userns_clone=0` or AppArmor policy denies userns, as
observed on ubuntu-latest in PR #88 run 34915813110) names the exact failed
capability and exits nonzero.

That retained report predates the `isolated_execution` capability. It is
historical evidence for the original probe, not a qualification of this repair.
Run the revised probe on the eventual integrated candidate and retain the
actual report separately from unit-test output.

## Review repair — 2026-09-15

The required Python 3.11 CI job 104354380103 exposed two PASS tests that used
the ambient Python manifest despite the qualification pin being 3.12. Those
tests now supply an explicit 3.12 fixture, and the CLI fixture output is
captured rather than mixed into live-looking capability logs. The same module
tests real manifest handling for 3.11/3.12/3.13 and numeric dependency versions
(for example, cryptography 4 is below 43, while 100 is above it).

Correction to the earlier PR review: the successful namespace fields printed
by that CI job came from `test_main_exit_codes_and_output_file` with mocked
subprocess/probe calls. They were not a live prerequisite PASS contradicting
the real M4 skips. The two matrix failures remain real. A new unmocked test
uses the same cached availability predicate as M4 and runs the revised probe;
BLOCKED is an acceptable prerequisite observation, never a containment PASS.
Separate failing regression cases require execution failure to block the
report even when namespace probes succeed.

The owner's concurrent update activated the workflow on this PR. That change
is preserved here. Its actual probe/zero-skips job must pass before acceptance;
activating the workflow does not supply a capable runner. This repair still
requires independent review.

## Non-claims and dependencies

* This PR changes no sandbox, runtime, or schema behaviour; it adds the
  probe runner, tests, a workflow, and evidence.
* A PASS here means only that the environment *can* construct the isolation
  boundary. It is **not** M4 qualification: final qualification requires the
  actual M4 execution gate of PR #88 **and** the repaired protected
  runtime/schema tracked by issue #108 (owned by Lane 1; not touched here).
* Passing probes do not prove containment; they only prove the prerequisite
  kernel features exist. The containment claim belongs to the isolated
  execution evidence itself.
* Timestamps and revision fields in the report are operator-asserted; the
  report is unsigned evidence, not a Station-signed receipt.
