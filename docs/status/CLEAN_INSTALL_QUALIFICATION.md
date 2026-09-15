# Clean-install qualification

`verifier/v3/qualify_clean_install.py` qualifies that the harness can be
built and installed as a wheel and used from a clean environment, bound to
an exact source commit. It is fail-closed: any failing step marks the report
FAIL and yields a non-zero exit code, and the evidence is still written.

## Steps

1. **Bind the source.** Resolve the checkout's `HEAD` commit and tree SHA
   via git. If git evidence is unavailable, the qualification fails.
2. **Build one wheel.** `pip wheel --no-deps` from the exact checkout;
   exactly one wheel must be produced. Its name and SHA-256 are recorded.
3. **Fresh-venv install.** A dedicated venv is created outside the checkout
   and the wheel is installed with the `factory,marketplace` extras (no test
   tools). `pip check` must pass and `pip freeze` is retained.
4. **Isolated smoke.** From a temporary directory outside the checkout, the
   venv's Python runs with `-I` and with `PYTHONPATH`/`PYTHONHOME` removed.
   Core modules (`residual`, Factory runtime/M4 surfaces, marketplace CLI,
   station server, `ai_providers`, `observation_layer`) must resolve to
   recorded distribution files inside the venv — checkout shadowing,
   global-site origins, or files not in the wheel manifest are failures.
   Station static/schema resources must be packaged, the Factory extra
   imports (`cryptography`, `yaml`) must resolve, and all four console
   scripts (`residual`, `residual-station`, `residual-worker`,
   `residual-module`) must exist and answer `--help`.
5. **Factory ownership gate.** `verifier/v3/check_factory_ownership.py`
   must pass against the checkout, binding the qualification to the
   #95-pinned Factory/M2/M3/M4 trust surface (32 protected paths, pinned at
   `50646c93ff5772e9ee1182ca6b4c290b1a5e7cba`).
6. **Report.** A machine-readable JSON report binds the commit SHA, tree
   SHA, wheel SHA-256, Python version, ownership-gate result, smoke results,
   and the installed dependency set.

## Running

```bash
python verifier/v3/qualify_clean_install.py \
  --source-root . --output runs/clean-install/report.json
```

The staged workflow `ci/clean-install-qualification.yml` runs this on a
Python 3.11/3.12/3.13 matrix for PRs and pushes to `main`. It is staged
outside `.github/workflows/` and must be moved into place by a maintainer
to become active.

The `test` extra (`pytest`, `PyYAML`) supports running the repository test
suite and the regression tests for this tooling
(`tests/test_clean_install_qualification.py`); it is not required by the
installed-wheel smoke, which deliberately runs without test tools.

## Non-claims

This is a package/clean-install qualification only. It does **not** qualify
measured evaluation results, does not replace the full source verifier
gates, does not make the trusted-fixture M4 lane an OS sandbox, does not
close any issue, and does not authorize benchmark or production claims.
