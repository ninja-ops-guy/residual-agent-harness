# Blank-VM installation procedure (release candidate)

Status: **procedure preparation only — certifies no release.** The protected
M4 integration gate is accepted on main
`22a5bae54ec12987ffd7a90d881fb4533c9b4b97`; final blank-environment execution
still targets a later designated release-candidate commit after the remaining
release/recovery integration gates are accepted.

Script: `scripts/release/blank_vm_install_check.py` (stdlib-only,
self-contained; fetch it to the bare machine, e.g. via the release's raw
URL). It deliberately shares the smoke surface with
`verifier/v3/qualify_clean_install.py` (#100) and the ownership gate from
`verifier/v3/check_factory_ownership.py` (#95).

## Prerequisites on the blank VM

- Python >= 3.10 with `venv` (nothing else; no repo checkout, no
  PYTHONPATH, no pre-seeded packages).
- Network reachability to the release artifact URL.
- The published artifact SHA-256, obtained through a trusted channel separate
  from the artifact bytes themselves (for example signed release metadata).

## Run

```bash
python3 blank_vm_install_check.py \
  --artifact-url https://<release>/residual_agent_harness-<ver>-py3-none-any.whl \
  --sha256 <published-sha256> \
  --out /evidence/blank-vm-install
# maintainer mode (with the release-candidate checkout present) adds:
#   --checkout /path/to/checkout   # runs the #95 ownership gate too
```

Exit code 0 = all required checks PASS. Exit 1 = fail-closed; evidence is
retained regardless. A procedure PASS is not a release verdict.

## Checks and detection points

| # | check_id | what it proves | failure detected here |
|---|----------|----------------|------------------------|
| 1 | `python_probe` | usable Python >= 3.10 | missing/too-old interpreter |
| 2 | `fetch_artifact` | artifact downloads (1 automatic retry) | network/URL failure |
| 3 | `verify_hash` | bytes == published digest | **corrupt download / supply swap** — install is never attempted |
| 4 | `create_venv` | fresh venv; pre-existing dir is wiped and the wipe is recorded | partial prior install |
| 5 | `install_artifact` | `pip install <wheel>[factory,marketplace]`, `pip check`, retained `pip freeze` | dependency-resolution failure, interrupted install |
| 6 | `isolated_smoke` | venv Python `-I`, outside any checkout: module origins inside venv site-packages and in the wheel manifest; packaged station resources; `cryptography`/`yaml` resolve; all 4 console scripts answer `--help` | broken/incomplete install |
| 7 | `ownership_gate` | #95 Factory/M2/M3/M4 trust surface intact (maintainer mode; `SKIP` on a true blank VM) | protected-path drift |

## Evidence and endpoint trust

`<out>/checks.jsonl` contains one typed record per check
(`check_id`, `status` PASS/FAIL/SKIP, `detail`, `log`, `recovery`,
`time_utc`, `prev_hash`). Records are hash-chained: each embeds the SHA-256 of
the previous line. `<out>/summary.json` records the final chain head, record
count, overall status and artifact identity; `<out>/logs/` retains command
stdout/stderr.

The chain's internal links and a summary stored beside that same chain are not,
by themselves, independent authentication of the final tail. For release use,
retain the final head/count or the complete summary through a trusted external
retention/signing channel and pass those retained values to
`blank_vm_install_check.verify_chain()`. Retain the complete evidence directory
unmodified as the detailed record, but do not infer authenticity merely from
all files agreeing with one another after the fact.

## Final release-candidate execution still required

Authoring/procedure validation exercised Python 3.12, network availability,
fresh-venv installation of the built 0.5.0 wheel with extras, isolated smoke,
and the ownership gate using controlled/local fixtures. That is not final
blank-OS evidence.

The designated release candidate must still be tested on a genuinely clean OS
image with no repository checkout or pre-seeded project packages, fetching the
actual published artifact through the production HTTPS release path and
verifying its digest against separately trusted release metadata. Retain exact
candidate commit/tree, OS/image, Python, artifact URL/digest and procedure
evidence identities. That final run remains separate from elapsed soak,
live-provider, production-reliability and research qualification gates.
