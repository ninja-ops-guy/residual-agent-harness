#!/usr/bin/env python3
"""Guided, offline source-checkout example; not a release qualification gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def source_identity() -> dict:
    identity = {"commit": None, "tree": None, "dirty": None}
    try:
        for key, ref in (("commit", "HEAD"), ("tree", "HEAD^{tree}")):
            identity[key] = subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", ref], text=True,
                stderr=subprocess.DEVNULL, timeout=10,
            ).strip()
        identity["dirty"] = bool(subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain"], text=True,
            stderr=subprocess.DEVNULL, timeout=10,
        ).strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return identity


def demonstrate(output: Path) -> dict:
    started = time.monotonic()
    # Exclusive directory creation prevents accidental replacement of a prior run.
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "schema": "residual.first-run.v1",
        "scope": "source-checkout-onboarding-only",
        "status": "INCOMPLETE",
        "source": source_identity(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "checks": [],
        "release_authority": False,
    }
    env = dict(os.environ, PYTHONPATH=str(ROOT))

    def command(label: str, args: list[str], expected: int = 0) -> str:
        proc = subprocess.run(
            [sys.executable, "-m", "residual", *args], cwd=output,
            env=env, capture_output=True, text=True, timeout=60,
        )
        (output / (label + ".log")).write_text(
            proc.stdout + proc.stderr, encoding="utf-8",
        )
        passed = proc.returncode == expected
        report["checks"].append({
            "name": label, "status": "PASS" if passed else "FAIL",
            "exit_code": proc.returncode, "expected_exit_code": expected,
        })
        if not passed:
            raise ValueError(f"{label} returned {proc.returncode}; expected {expected}")
        return proc.stdout

    try:
        shutil.copytree(ROOT / "examples/onboarding/sample_project", output / "sample")
        shutil.copyfile(ROOT / "examples/onboarding/config.toml", output / "config.toml")
        print("1/3 Check the sample inventory (no model or account required).")
        command("run", ["run", "sample/task.json", "--config", "config.toml", "--output", "accepted"])
        result_path = output / "accepted/result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (result.get("success") is not True
                or result.get("values") != {"total_fan_rpm": 7230, "total_temperature": 65.25}
                or result.get("metrics", {}).get("calls") != 0):
            raise ValueError("sample did not return the expected verified values with zero model calls")
        report["model_calls"] = result["metrics"]["calls"]
        print("    Verified totals: 7,230 RPM and 65.25 degrees C (sum of readings).")

        print("2/3 Check that the saved result matches its evidence trace.")
        trace_args = ["verify-trace", "accepted/trace.jsonl"]
        command("verify", [*trace_args, "--result", "accepted/result.json"])
        # Preserve the original. Demonstrate a changed result against the same trace.
        altered = json.loads(result_path.read_text(encoding="utf-8"))
        altered["values"]["total_fan_rpm"] = 0
        write_json(output / "altered-result.json", altered)

        print("3/3 Deliberately alter a COPY of the result; require rejection.")
        command("reject-altered", [*trace_args, "--result", "altered-result.json"], expected=1)
        command("verify-original-again", [*trace_args, "--result", "accepted/result.json"])
        report["artifacts"] = {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ("accepted/result.json", "accepted/trace.jsonl", "altered-result.json")
        }
        report["status"] = "PASS"
        return report
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report["status"] = "FAIL"
        report["error"] = str(error)
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_json(output / "first-run.json", report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="runs/first-run", help="New directory; existing paths are refused")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    print("RESIDUAL first run — deterministic example in a development checkout.")
    try:
        demonstrate(output)
    except FileExistsError:
        print("That output path already exists. Choose a new --output directory; previous evidence is preserved.", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"First run did not complete: {error}. Inspect {output} for retained diagnostics.", file=sys.stderr)
        return 1
    print(f"Example complete. Inspect {output / 'first-run.json'} and the accepted/ files.")
    print("This shows local result/trace consistency and rejection of this alteration.")
    print("It does not prove origin authenticity, live-agent quality, or release readiness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
