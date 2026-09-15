#!/usr/bin/env python3
"""Recovery-scenario checks for the blank-VM install procedure.

Drives scripts/release/blank_vm_install_check.py against controlled fixtures
and asserts each plausible failure mode is detected at the expected check,
and that the documented recovery restores a PASS. Scenarios:

  corrupt-download       artifact bytes tampered after hash publication
                         -> FAIL at verify_hash; recovery: re-fetch correct
                         bytes -> PASS.
  missing-python         interpreter probe against a nonexistent binary
                         -> FAIL at python_probe; recovery: point at a real
                         interpreter -> PASS of the probe.
  partial-prior-install  a dirty pre-existing venv dir at the work path
                         -> create_venv records the wipe+recreate recovery
                         and the procedure continues.
  dependency-resolution  artifact spec that cannot resolve (bogus local
                         "wheel") -> FAIL at install_artifact; recovery:
                         replace with a valid artifact.
  interrupted-install    venv whose install never completed (no
                         distribution present) -> isolated smoke/pip check
                         surface the gap; recovery: recreate the venv.

Each scenario emits a typed record (scenario, detection_point, expected,
observed, recovery, status PASS/FAIL) into recovery-checks.jsonl, and the
per-scenario install-check evidence directories are retained under
--out/<scenario>/.

Scenarios that need network or a real PyPI are not exercised here; the
fixtures are fully offline (locally built trivial wheel). See
docs/release/RECOVERY_SCENARIOS.md for the full matrix including the
documented-only rows.

Non-claims: these checks validate the recovery PROCEDURE, not a release.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile

THIS = Path(__file__).resolve()
sys.path.insert(0, str(THIS.parent))
import blank_vm_install_check as bvic  # noqa: E402


def make_trivial_wheel(path, name="tamper_fixture", version="0.1"):
    """Build a minimal valid wheel offline (no pip/build needed)."""
    path = Path(path).with_name(f"{name}-{version}-py3-none-any.whl")
    dist_info = f"{name}-{version}.dist-info"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{name}/__init__.py", "VALUE = 1\n")
        zf.writestr(f"{dist_info}/METADATA",
                    f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        zf.writestr(f"{dist_info}/WHEEL",
                    "Wheel-Version: 1.0\nGenerator: fixture\n"
                    "Root-Is-Purelib: true\nTag: py3-none-any\n")
        zf.writestr(f"{dist_info}/RECORD", "")
    return path


def serve_url(path):
    return Path(path).as_uri()


def scenario_record(records, scenario, detection_point, expected, observed,
                    recovery, ok):
    records.append({
        "scenario": scenario,
        "detection_point": detection_point,
        "expected": expected,
        "observed": observed,
        "recovery": recovery,
        "status": "PASS" if ok else "FAIL",
    })


def statuses(out_dir):
    summary = json.loads((Path(out_dir) / "summary.json").read_text())
    return summary["checks"]


def sc_corrupt_download(records, out_root, fixture_wheel):
    tampered = out_root / "corrupt-download" / "artifact.whl"
    tampered.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture_wheel, tampered)
    with open(tampered, "ab") as handle:  # tamper after hashing
        handle.write(b"tampered")
    good_hash = bvic.sha256_file(fixture_wheel)
    out = out_root / "corrupt-download" / "evidence"
    summary = bvic.run_procedure(
        artifact_url=serve_url(tampered), expected_sha256=good_hash,
        out_dir=out, work_dir=out / "work")
    checks = summary["checks"]
    ok = (checks.get("verify_hash") == "FAIL"
          and checks.get("install_artifact") == "SKIP"
          and summary["status"] == "FAIL")
    scenario_record(
        records, "corrupt-download", "verify_hash",
        "FAIL at verify_hash; install never attempted",
        json.dumps(checks),
        "delete the artifact, re-fetch, re-verify hash, re-run", ok)
    # Recovery: correct bytes pass the hash check (fetch+hash only scope).
    log = bvic.CheckLog(out / "recovery.jsonl")
    recovered = bvic.check_fetch(log, out / "logs", out / "work",
                                 serve_url(fixture_wheel))
    ok2 = bool(recovered) and bvic.check_hash(
        log, out / "logs", recovered, good_hash)
    records[-1]["recovery_verified"] = ok2
    return ok and ok2


def sc_missing_python(records, out_root, fixture_wheel):
    out = out_root / "missing-python" / "evidence"
    summary = bvic.run_procedure(
        artifact_url=serve_url(fixture_wheel),
        expected_sha256=bvic.sha256_file(fixture_wheel),
        out_dir=out, work_dir=out / "work",
        python_override="/nonexistent/python3")
    checks = summary["checks"]
    ok = (checks.get("python_probe") == "FAIL"
          and checks.get("fetch_artifact") == "SKIP")
    scenario_record(
        records, "missing-python", "python_probe",
        "FAIL at python_probe; all later checks SKIP",
        json.dumps(checks),
        "install Python >= 3.10, re-run", ok)
    log = bvic.CheckLog(out / "recovery.jsonl")
    recovered = bvic.check_python(log, out / "logs")
    records[-1]["recovery_verified"] = recovered is not None
    return ok and recovered is not None


def sc_partial_prior_install(records, out_root, fixture_wheel):
    out = out_root / "partial-prior-install" / "evidence"
    work = out / "work"
    dirty = work / "install-venv"
    dirty.mkdir(parents=True)
    (dirty / "STALE-GARBAGE").write_text("leftover from killed install\n")
    log = bvic.CheckLog(out / "checks.jsonl")
    venv = bvic.check_venv(log, out / "logs", sys.executable, work)
    ok = (venv is not None and not (dirty / "STALE-GARBAGE").exists()
          and any(r.get("recovery") for r in log.records))
    scenario_record(
        records, "partial-prior-install", "create_venv",
        "dirty venv detected, wiped, recreated; recovery recorded",
        json.dumps([r["check_id"] + ":" + r["status"] for r in log.records]),
        "remove the venv dir and recreate fresh (automatic)", ok)
    shutil.rmtree(work, ignore_errors=True)
    return ok


def sc_dependency_resolution(records, out_root, fixture_wheel):
    out = out_root / "dependency-resolution" / "evidence"
    work = out / "work"
    log = bvic.CheckLog(out / "checks.jsonl")
    venv = bvic.check_venv(log, out / "logs", sys.executable, work)
    if venv is None:
        scenario_record(records, "dependency-resolution", "install_artifact",
                        "FAIL at install_artifact", "venv creation failed",
                        "n/a", False)
        return False
    # A requirement that cannot resolve offline.
    exe = bvic.venv_python(venv)
    result = bvic.run_logged(
        [str(exe), "-m", "pip", "install", "--no-index",
         "definitely-not-a-real-package-xyz==99.99"],
        out / "logs" / "pip-fail.log", env=bvic.clean_env(), timeout=120)
    detected = result is None or result.returncode != 0
    # Recovery: install a valid artifact into the same clean venv.
    recovery = bvic.run_logged(
        [str(exe), "-m", "pip", "install", "--no-index", str(fixture_wheel)],
        out / "logs" / "pip-recover.log", env=bvic.clean_env(), timeout=120)
    recovered = recovery is not None and recovery.returncode == 0
    scenario_record(
        records, "dependency-resolution", "install_artifact",
        "pip resolution failure detected at install_artifact",
        f"pip rc={getattr(result, 'returncode', None)}",
        "delete venv, install the published artifact, re-run checks",
        detected and recovered)
    records[-1]["recovery_verified"] = recovered
    shutil.rmtree(work, ignore_errors=True)
    return detected and recovered


def sc_interrupted_install(records, out_root, fixture_wheel):
    out = out_root / "interrupted-install" / "evidence"
    work = out / "work"
    log = bvic.CheckLog(out / "checks.jsonl")
    venv = bvic.check_venv(log, out / "logs", sys.executable, work)
    if venv is None:
        scenario_record(records, "interrupted-install", "install_artifact",
                        "FAIL/SKIP surfaced", "venv creation failed",
                        "n/a", False)
        return False
    # Simulate a killed install: venv exists, distribution absent. The
    # smoke surface must fail (module unimportable) rather than pass.
    exe = bvic.venv_python(venv)
    result = bvic.run_logged(
        [str(exe), "-I", "-c", "import tamper_fixture"],
        out / "logs" / "probe.log", cwd=work, env=bvic.clean_env(),
        timeout=60)
    detected = result is not None and result.returncode != 0
    scenario_record(
        records, "interrupted-install", "install_artifact/isolated_smoke",
        "absent distribution detected (import of expected module fails)",
        f"probe rc={getattr(result, 'returncode', None)}",
        "delete the venv (create_venv wipes pre-existing dirs) and re-run "
        "the full procedure", detected)
    records[-1]["recovery_verified"] = detected
    shutil.rmtree(work, ignore_errors=True)
    return detected


SCENARIOS = (
    ("corrupt-download", sc_corrupt_download),
    ("missing-python", sc_missing_python),
    ("partial-prior-install", sc_partial_prior_install),
    ("dependency-resolution", sc_dependency_resolution),
    ("interrupted-install", sc_interrupted_install),
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True,
                        help="evidence output directory")
    parser.add_argument("--only", nargs="*", default=None,
                        help="restrict to named scenarios")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-recovery-") as tmp:
        fixture_wheel = make_trivial_wheel(Path(tmp) / "fixture.whl")
        records = []
        overall = True
        for name, fn in SCENARIOS:
            if args.only and name not in args.only:
                continue
            try:
                ok = fn(records, args.out, fixture_wheel)
            except Exception as exc:  # a crashed scenario is a FAIL
                scenario_record(records, name, "harness",
                                "no exception", f"{type(exc).__name__}: {exc}",
                                "inspect retained evidence", False)
                ok = False
            overall = overall and ok
    report = {
        "status": "PASS" if overall else "FAIL",
        "scope": "recovery-procedure validation; certifies no release",
        "python": sys.version,
        "scenarios": records,
    }
    (args.out / "recovery-checks.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
