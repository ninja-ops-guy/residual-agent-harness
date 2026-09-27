# Test environment matrix

Date: 2026-09-23 America/New_York (runs completed 2026-09-24 UTC)

Scope: read-only triage of the reported broad-suite result. No R4.1 file was
modified, no canary was executed, and no product/test repair was attempted.

## Source identity

- Branch under test: `main`
- Branch SHA: `2f9dda3882f39c28a1c766859b1bf9579eea7911`
- `origin/main` SHA when reproduction began:
  `2f9dda3882f39c28a1c766859b1bf9579eea7911`
- Current `origin/main` SHA after the required final fetch:
  `d796f36b75e730a0bab71bdba564206174393719`
- Tree: the clean tracked tree at that commit
- Triage documentation branch: `docs/test-environment-triage`
- R4.1 candidate/qualification artifacts: not opened for execution and not
  modified

## Executed environments

| ID | Python | OS/runtime | Dependencies/extras | Relevant environment | Command | Result | Interpretation |
|---|---|---|---|---|---|---|---|
| E1 | CPython 3.11.0rc1 | Ubuntu 22.04.5 under WSL2, Linux 6.6.87.2; managed process sandbox denies `socket()` | `defusedxml 0.7.1`, `pytest 9.1.1`, `PyYAML 6.0.3`; no `cryptography`; editable core package only | `RESIDUAL_HOME` and `CI` removed; no provider credentials; `PYTHONDONTWRITEBYTECODE=1` | `python -m unittest discover -s tests -q` | 1121 run; 5 failures; 95 errors; 29 skips | Exact reproduction of the reported aggregate |
| E2 | CPython 3.11.0rc1 | Same WSL2 host, outside the managed process sandbox; loopback and subprocess/kernel features available | Same incomplete dependency set as E1 | Same variable cleanup | Focused `python -m unittest -v` over all 33 socket-error tests and all 5 failed tests | 87/87 passed | Deterministically attributes 33 errors and all 5 failures to E1 setup |
| E3 | CPython 3.11.0rc1 | Same WSL2 host, outside managed sandbox; checkout on Windows DrvFS | isolated venv; editable `.[factory]`; `cryptography 50.0.1`, `PyYAML 6.0.3`, `defusedxml 0.7.1`, `pytest 9.1.1` | Same variable cleanup | `python scripts/qualification_unittest.py discover -s tests -q` | 1155 run; 17 failures; 1 error | The 62 missing-crypto errors disappear. M4 isolation tests become runnable but fail because this WSL/DrvFS host is not a capable qualification runner. This is a separate environment result, not a regression in the reported aggregate. |
| E4 | CPython 3.13.5 | Native Windows | Global, non-isolated environment; includes `cryptography 49.0.0`, `PyYAML 6.0.3`, `pytest 9.0.3`, and many unrelated packages | Ambient Windows environment | `python.exe -m unittest discover -s tests -q` | 835 run; 4 failures; 180 errors | Diagnostic only. `resource` imports, `os.geteuid`, symlink privilege, POSIX shell paths, and CRLF comparisons show that native Windows is not a supported full-suite qualification target. |
| E5 | CPython 3.12.12 (retained repository evidence) | Native Linux, kernel 5.10.134-18.0.12, glibc 2.36, capable user/mount/PID/network/IPC/UTS namespaces | `cryptography 44.0.2`, `PyYAML 6.0.2`; factory qualification dependencies | See `docs/m4-qualification-runner-prereqs.md` | M4 prerequisite probe plus zero-skip M4 suite | Historical PASS at its recorded SHA | Establishes the known shape of a capable M4 qualification runner; it is not fresh evidence for `2f9dda38`. |

## Reported-result classification counts

The outcome column classifies the 129 non-passing outcomes in E1; those counts
are mutually exclusive. The ancillary column counts run-level findings that
do not replace an outcome's causal classification.

| Classification | Reported outcomes | Ancillary findings | Basis |
|---|---:|---:|---|
| `ENVIRONMENT_SETUP` | 38 | 0 | 33 loopback socket errors plus 5 runtime/watchdog failures; all affected focused tests passed outside the managed process sandbox |
| `MISSING_OPTIONAL_DEPENDENCY` | 62 | 0 | Every error was `EvidenceError: cryptography Ed25519 support is required`; `cryptography>=43` is declared by the `factory` extra and installed by CI |
| `STALE_BRANCH` | 0 | 1 | The test SHA equalled `origin/main` at reproduction start, but final fetch advanced main to `d796f36b`; findings are bounded to `2f9dda38` |
| `TEST_DISCOVERY` | 0 | 1 | The reported 1121 count is exactly reproduced by unittest; raw pytest separately collects 1884 and is not the same suite |
| `PLATFORM_SPECIFIC` | 0 | 1 | No reported E1 outcome needs this category; the native-Windows diagnostic is a separate platform finding |
| `EXPECTED_SKIP` | 29 | 0 | 22 namespace-isolation skips and 7 libseccomp/backend skips, each explicit and expected on E1 |
| `HISTORICAL_FAILURE` | 0 | 0 | No reported outcome required historical-only attribution |
| `REAL_REGRESSION` | 0 | 0 | No reported failure remained under the applicable focused environment |
| `UNKNOWN` | 0 | 0 | Every reported non-passing outcome has a deterministic common cause |

Passing outcomes: 992 (`1121 - 5 - 95 - 29`). They are not assigned a
failure classification.

## Minimum supported environments

### Development / ordinary full source suite

The minimum supported development shape is:

- CPython 3.11 or newer (stable release; CI covers 3.11, 3.12, and 3.13);
- Linux/POSIX runtime for the broad source suite;
- a native Linux filesystem is preferred and required for qualification
  conclusions involving the isolated verifier;
- local loopback socket creation permitted;
- subprocess creation, Git, and ordinary temporary-file operations permitted;
- installation with `.[factory]` plus `pytest` (this provides
  `cryptography>=43`, `PyYAML>=6`, and the core `defusedxml>=0.7.1,<1`);
- no provider credentials are required;
- unavailable kernel isolation may produce the 29 explicit skips in an
  ordinary development run, but such a run does not qualify M4 containment.

The observed 3.11.0 release candidate is useful reproduction evidence but is
not the recommended minimum. Use a stable, currently supported CPython 3.11
patch release.

### Qualification environment

Qualification requires all development requirements plus:

- native Linux on a capable runner (the repository currently targets
  `ubuntu-22.04` for the M4 job);
- Python 3.12 for the pinned M4 prerequisite gate;
- working user, mount, PID, network, IPC, and UTS namespaces;
- `unshare --kill-child`, `os.chroot`, and successful real isolated execution;
- the M4 prerequisite report must be `PASS`, and the M4 test lane must contain
  zero skips.

WSL2 over a Windows DrvFS checkout is suitable for ordinary development but
is not the minimum qualification environment: E3's probe/run mismatch and
isolated execution failures prevent a qualification claim.

## Recommended CI matrix

| Lane | OS | Python | Install | Command/gate | Required disposition |
|---|---|---:|---|---|---|
| Full source | `ubuntu-22.04` (or reviewed successor) | 3.11 | `pip install '.[factory,qualification]' pytest` on current main | `python scripts/qualification_unittest.py discover -s tests -v` | No failures/errors; declared skips recorded |
| Full source | same | 3.12 | same | same | No failures/errors; declared skips recorded |
| Full source | same | 3.13 | same | same | No failures/errors; declared skips recorded |
| M4 qualification | reviewed capable native-Linux runner | 3.12 | `pip install -e '.[factory]' pytest` | prerequisite probe, focused M4 pytest lane, zero-skip check | Probe PASS and zero skips |
| Clean install | Linux | 3.11, 3.12, 3.13 | wheel flow defined by verifier | `verifier/v3/qualify_clean_install.py` workflow | PASS at exact SHA |
| Native Windows diagnostic | Windows | 3.13 | `.[factory]` | selected explicitly portable tests only | Non-blocking until Windows is declared supported |

Do not put raw `pytest` at the root in place of the authoritative unittest
command. On this tree, `pytest --collect-only` found 1884 items, including
`tests/enterprise` and `vendor/user-modules`; that is a different discovery
surface from the reported 1121-test run.

## Readiness impact

- Canary: no reported outcome blocks canary on regression grounds. The canary
  was not executed. The tested SHA is now stale relative to current main, so
  this triage cannot qualify or clear `d796f36b`. Existing R4.1 authorization
  and gates remain authoritative.
- Production: the reported aggregate is not valid production-qualification
  evidence because its environment omitted a required extra, denied loopback
  sockets, and skipped the kernel-isolation lanes.
- A production or M4-containment readiness claim still requires the capable
  native-Linux qualification lane to pass at the exact candidate SHA with zero
  M4 skips. E1/E2/E3 do not provide that evidence.
