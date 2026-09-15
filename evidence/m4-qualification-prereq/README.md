# M4 qualification prerequisite probe — local evidence

Captured 2026-09-15 by running the new
`residual/factory/m4_qualification_prereq.py` against main tip
`eefee6ac005c93278f483e002e38a768920f0fae` (public tarball), plus the new
module's own source, in this agent's local Linux sandbox.

* `local-probe-report.json` — machine-readable PASS/BLOCKED report (schema
  `m4-qualification-prereq-report-v1`), revision-bound to the tested SHA.
  Result here: **PASS** on all 11 capabilities (this kernel permits
  unprivileged user namespaces: `max_user_namespaces=22829`,
  `unprivileged_userns_clone=1`).
* `local-probe-stdout.txt` — raw CLI stdout, exit code 0.
* `local-tests.txt` — `pytest tests/test_factory_m4_sandbox.py
  tests/test_factory_m4_qualification_prereq.py -q`: 30 passed, 0 skipped.

This is a positive capability datapoint only: it shows the environment can
construct the `linux-userns-isolated-v1` boundary. It is not M4
qualification, which requires the PR #88 execution gate and the repaired
runtime from issue #108. On a runner without userns support (as in PR #88
run 34915813110 on ubuntu-latest) the same runner reports BLOCKED with the
failed capability named and exits 1.
