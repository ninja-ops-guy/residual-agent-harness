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

The staged workflow `ci/m4-qualification-prereq.yml` (to be moved to
`.github/workflows/` by a maintainer with a `workflow`-scoped token) runs the
probes, the probe regression tests, and the M4 sandbox test suite with a
zero-skips requirement (the same skip-rejection check PR #88 introduced).

## Local evidence

This environment (Linux 5.10.134-18.0.12 lifsea kernel, x86_64, glibc 2.36,
`max_user_namespaces=22829`, `unprivileged_userns_clone=1`, Python 3.12.12,
cryptography 44.0.2, PyYAML 6.0.2) reported **PASS** on every capability,
and the full `tests/test_factory_m4_sandbox.py` suite ran with 0 skips.
Retained under `evidence/m4-qualification-prereq/` and bound to main tip
`eefee6ac005c93278f483e002e38a768920f0fae`. A BLOCKED report (e.g. a runner
where `unprivileged_userns_clone=0` or AppArmor policy denies userns, as
observed on ubuntu-latest in PR #88 run 34915813110) names the exact failed
capability and exits nonzero.

## Non-claims and dependencies

* This PR changes no sandbox, runtime, or schema behaviour; it adds the
  probe runner, tests, a staged workflow, and evidence.
* A PASS here means only that the environment *can* construct the isolation
  boundary. It is **not** M4 qualification: final qualification requires the
  actual M4 execution gate of PR #88 **and** the repaired protected
  runtime/schema tracked by issue #108 (owned by Lane 1; not touched here).
* Passing probes do not prove containment; they only prove the prerequisite
  kernel features exist. The containment claim belongs to the isolated
  execution evidence itself.
* Timestamps and revision fields in the report are operator-asserted; the
  report is unsigned evidence, not a Station-signed receipt.
