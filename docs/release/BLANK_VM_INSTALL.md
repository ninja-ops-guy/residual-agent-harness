# Blank-VM installation procedure (release candidate)

Status: **procedure preparation only — certifies no release.** Final runs
target the accepted release candidate after the #108 sandbox-timing repair
lands and the candidate commit is designated.

Script: `scripts/release/blank_vm_install_check.py` (stdlib-only,
self-contained; fetch it to the bare machine, e.g. via the release's raw
URL). It deliberately shares the smoke surface with
`verifier/v3/qualify_clean_install.py` (#100) and the ownership gate from
`verifier/v3/check_factory_ownership.py` (#95).

## Prerequisites on the blank VM

- Python >= 3.10 with `venv` (nothing else; no repo checkout, no
  PYTHONPATH, no pre-seeded packages).
- Network reachability to the release artifact URL.
- The published artifact SHA-256, obtained over a separate channel from
  the download (release notes / signed announcement).

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
retained regardless.

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

## Evidence

`<out>/checks.jsonl` — one typed record per check
(`check_id`, `status` PASS/FAIL/SKIP, `detail`, `log`, `recovery`,
`time_utc`, `prev_hash`). Records are hash-chained: each embeds the
SHA-256 of the previous line; verify with
`blank_vm_install_check.verify_chain()`. `<out>/summary.json` carries the
chain head and the overall status. `<out>/logs/` retains every command's
stdout/stderr. Retain the whole directory unmodified.

## Environment limitations (this sandbox)

Validated live in the authoring sandbox (probe output: `python3 --version`
= 3.12; `curl` to github.com OK; `pip install` into a fresh venv OK):
fetch, hash, venv, real install of the built 0.5.0 wheel with extras,
isolated smoke, and the ownership gate all PASS against a `file://`
artifact URL. **Not** validated here: a truly bare OS image (the sandbox
has Python and network pre-provisioned), and HTTPS fetch from a real
release host (a `file://` URL exercised the same code path; the HTTPS
branch differs only in `urllib` transport). Both are documented-only and
must be exercised on the release-candidate run.
