# Broad-suite reproduction

This procedure reproduces and separates the `1121 / 5 / 95 / 29` result.
It does not run the canary and does not exercise or modify R4.1.

## Identity and safety checks

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
python --version
python -c 'import platform; print(platform.platform())'
```

Source identity for this record:

```text
tested HEAD                         2f9dda3882f39c28a1c766859b1bf9579eea7911
origin/main at reproduction start  2f9dda3882f39c28a1c766859b1bf9579eea7911
origin/main after final fetch       d796f36b75e730a0bab71bdba564206174393719
```

The branch was current when reproduction began and stale when the final remote
check completed. All causal findings are therefore bounded to `2f9dda38`; this
record does not claim a broad-suite result for current main.

Capture relevant variables by name, never secret values:

```bash
env | LC_ALL=C sort | grep -E '^(CI|PYTHON|PYTEST|RESIDUAL|GITHUB|VIRTUAL_ENV)='
```

The triage runs removed `RESIDUAL_HOME` and `CI`. No provider credential was
needed or inspected.

## Reproduce the reported aggregate

Use an environment with the core and test tools installed, without the
`factory` extra, and a process sandbox that denies socket creation:

```bash
env -u RESIDUAL_HOME -u CI PYTHONDONTWRITEBYTECODE=1 \
  python -m unittest discover -s tests -q
```

Observed twice:

```text
Ran 1121 tests
FAILED (failures=5, errors=95, skipped=29)
```

Error partition:

```text
33  PermissionError: [Errno 1] Operation not permitted
62  EvidenceError: cryptography Ed25519 support is required
```

The 33 permission errors occur at loopback/local socket creation. The five
assertion failures are listed exactly in `TEST_FAILURE_CLASSIFICATION.json`.

## Isolate socket and runtime failures

On the same WSL host outside the managed process sandbox, with the same
incomplete dependency set, run:

```bash
env -u RESIDUAL_HOME -u CI PYTHONDONTWRITEBYTECODE=1 \
  python -m unittest -v \
  tests.modular.test_adapters \
  tests.modular.test_routing \
  tests.station.test_station \
  tests.test_authority_lab \
  tests.test_providers \
  tests.test_factory_runtime_startup \
  tests.test_sandbox_timing_determinism.JournalContentionReadTests \
  tests.test_sandbox_timing_determinism.LeaseTriStateTests
```

Observed:

```text
Ran 87 tests in 23.767s
OK
```

This includes all 33 socket-error cases and all five failed cases. Their
pass outside the managed process sandbox is deterministic counterevidence to
a product-regression classification.

## Install the declared dependency set

Create a disposable environment outside the checkout:

```bash
python -m venv /tmp/residual-triage-py311
/tmp/residual-triage-py311/bin/python -m pip install -e '.[factory]' pytest
/tmp/residual-triage-py311/bin/python -m pip freeze
```

Relevant resolved packages in this run:

```text
cryptography==50.0.1
PyYAML==6.0.3
defusedxml==0.7.1
pytest==9.1.1
```

The project requirement is `cryptography>=43`, not the exact observed patch
version. After this install, none of the 62 Ed25519 errors remained.

Run the CI-shaped suite with:

```bash
env -u RESIDUAL_HOME -u CI PYTHONDONTWRITEBYTECODE=1 \
  /tmp/residual-triage-py311/bin/python \
  scripts/qualification_unittest.py discover -s tests -q
```

On the observed WSL2/DrvFS host, this made the M4 isolation predicate true,
expanded execution from 1121 to 1155 tests, and produced 17 failures plus one
error in real isolated-execution tests. This host is therefore not a capable
qualification runner. Do not reinterpret that result as a regression or
silence it with skips; run the M4 prerequisite gate on the specified native
Linux qualification host.

## Check expected skips

Run the authoritative command with `-v` and inspect skip reasons:

```bash
python scripts/qualification_unittest.py discover -s tests -v
```

The reported run contained:

```text
22 skipped: kernel namespace isolation unavailable on this platform
 7 skipped: libseccomp/kernel backend unavailable (no fallback)
```

These skips are acceptable only for an ordinary development run. M4
qualification explicitly requires zero skips.

## Discovery control

The reported count belongs to unittest discovery. Raw pytest is different:

```bash
python -m pytest --collect-only -q -p no:cacheprovider
```

Observed: 1884 collected items, including enterprise and vendored tests.
Use the repository CI command for like-for-like comparison:

```bash
python scripts/qualification_unittest.py discover -s tests -v
```

## Native Windows diagnostic

Native Windows Python 3.13.5 collected only 835 unittest cases and returned
four failures plus 180 errors. Dominant causes were 73 missing POSIX `resource`
imports, missing `os.geteuid`, symlink privilege errors, POSIX shell/path
assumptions, and CRLF-sensitive fixture comparisons. This confirms that the
full source qualification suite currently targets Linux; Windows should use a
separate explicitly portable diagnostic subset until support is declared.

## Qualification decision

Before treating a run as qualification evidence:

1. on current main, install `.[factory,qualification]` and pytest (the tested
   historical SHA predated the `qualification` extra);
2. use stable Python 3.11/3.12/3.13 for the ordinary matrix;
3. permit loopback and required subprocess operations;
4. for M4, use the pinned Python 3.12 native-Linux capable runner;
5. require the prerequisite report to PASS and require zero M4 skips;
6. bind results to exact branch/main SHAs and retain the dependency manifest.

No command in this record authorizes or invokes the canary.
