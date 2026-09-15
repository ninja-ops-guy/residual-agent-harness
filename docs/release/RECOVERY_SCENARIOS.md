# Recovery scenarios — detection points and recovery procedures

Companion to `BLANK_VM_INSTALL.md`. Scripted, offline-validated checks live
in `scripts/release/recovery_check.py`; each scenario asserts the failure
is detected at the expected check and that the documented recovery restores
a passing state. Per-scenario evidence is retained under
`<out>/<scenario>/`. Non-claims: this validates the recovery *procedure*,
not a release.

| Scenario | Detection point (check_id) | Detection signal | Recovery procedure | Scripted? |
|---|---|---|---|---|
| Corrupt download (truncated/tampered bytes) | `verify_hash` | computed SHA-256 ≠ published digest; `install_artifact` and later checks SKIP — the corrupt artifact never reaches a venv | Delete the file, re-fetch (the fetch check already retries once), re-verify the hash; if the mismatch reproduces from the same URL, treat as a supply incident and halt the release | Yes — live |
| Missing Python (bare VM) | `python_probe` | interpreter absent/unrunnable, or version < 3.10; every later check SKIP | Install Python >= 3.10 (and the OS `python3-venv` package), re-run from check 1 | Yes — live |
| Interrupted install (killed pip / power loss) | `install_artifact` (`pip check`) and `isolated_smoke` | inconsistent installed set; expected modules unimportable in the venv | Delete the venv and re-run; `create_venv` wipes pre-existing venv dirs automatically and records the wipe | Yes — live |
| Dependency resolution failure (index outage, metadata conflict) | `install_artifact` | `pip install` non-zero exit; full resolver output retained in `logs/05-install.log` | Retry once (transient index). If it reproduces, the artifact metadata or index reachability is at fault — halt the release candidate; do not hand-pin on the VM | Yes — live (offline, `--no-index`) |
| Partial prior install (re-run on a dirty machine) | `create_venv` | pre-existing `install-venv` dir found at the work path | Automatic: the dir is removed, a fresh venv is created, and the recovery is recorded in the check record's `recovery` field | Yes — live |
| HTTPS/transport failure from the release host | `fetch_artifact` | `urllib` error retained in `logs/02-fetch-attempt*.log` | Verify URL and network; re-run. (Documented-only in the authoring sandbox: exercised via `file://` URL; HTTPS differs only in transport) | Documented-only |
| Ownership gate failure (maintainer mode) | `ownership_gate` | `check_factory_ownership.py` non-zero; output retained | Halt the release; protected-path drift is a Lane-1/#108-domain repair, never patched in the release lane | Exercised live in PASS form; failure form by inspection |

Run the scripted scenarios:

```bash
python3 scripts/release/recovery_check.py --out runs/release-recovery
```

Overall PASS requires every scenario's expected detection **and** verified
recovery (`recovery_verified: true` in `recovery-checks.json`). A crashed
scenario is recorded FAIL with the exception retained.
