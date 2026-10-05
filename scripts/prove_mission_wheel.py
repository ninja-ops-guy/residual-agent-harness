"""Build/install the exact candidate and test outside the source tree.

This is software/package proof, not a native harness, independent install,
owner acceptance, factory ownership baseline advance, or release gate bypass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile


def run(args, *, cwd, env=None):
    return subprocess.run([str(a) for a in args], cwd=cwd, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"schema": "residual.mission-wheel-proof.v1", "status": "FAIL",
              "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip(),
              "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=source, text=True).strip(),
              "installed_native_proven": False, "independent_install_proven": False,
              "release_authorized": False}
    failures = []
    try:
        with tempfile.TemporaryDirectory(prefix="mission-wheel-") as temp:
            root = Path(temp)
            wheels = root / "dist"
            build = run([sys.executable, "-m", "pip", "wheel", source, "--no-deps", "-w", wheels], cwd=root)
            (output / "wheel-build.log").write_text(build.stdout)
            if build.returncode:
                raise RuntimeError("wheel build failed")
            candidates = list(wheels.glob("residual_agent_harness-*.whl"))
            if len(candidates) != 1:
                raise RuntimeError("expected exactly one candidate wheel")
            wheel = candidates[0]
            report["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
            report["wheel_name"] = wheel.name
            shutil.copy2(wheel, output / wheel.name)
            manifest = {}
            with zipfile.ZipFile(wheel) as archive:
                for name in archive.namelist():
                    if name.startswith(("residual/", "ai_providers/", "observation_layer/")) and (source / name).is_file():
                        raw = archive.read(name)
                        if raw != (source / name).read_bytes():
                            raise RuntimeError("wheel/source mismatch: " + name)
                        manifest[name] = hashlib.sha256(raw).hexdigest()
            report["source_matched_files"] = len(manifest)
            environment = root / "venv"
            venv.EnvBuilder(with_pip=True).create(environment)
            scripts = environment / ("Scripts" if os.name == "nt" else "bin")
            python = scripts / ("python.exe" if os.name == "nt" else "python")
            installed = run([python, "-m", "pip", "install", str(wheel) + "[factory]"], cwd=root)
            (output / "wheel-install.log").write_text(installed.stdout)
            if installed.returncode:
                raise RuntimeError("wheel install failed")
            isolated = root / "isolated"
            isolated.mkdir()
            # A poisoned cwd must never be used as the package or kernel source.
            (isolated / "residual.py").write_text("raise RuntimeError('source shadow imported')\n")
            (isolated / "AUTH_INVARIANTS.md").write_text("not the candidate spec\n")
            test = isolated / "test_mission_composed_authority.py"
            shutil.copy2(source / "tests/test_mission_composed_authority.py", test)
            adapter = isolated / "client.mjs"
            shutil.copy2(source / "integrations/mission-sync/openclaw/client.mjs", adapter)
            report["node_adapter_sha256"] = hashlib.sha256(adapter.read_bytes()).hexdigest()
            report["test_sha256"] = hashlib.sha256(test.read_bytes()).hexdigest()
            manifest_path = isolated / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            probe = isolated / "probe.py"
            probe.write_text('''import hashlib, importlib.metadata, json, pathlib, sys
import residual
from residual import authority_kernel
root = pathlib.Path(residual.__file__).resolve().parent.parent
assert root.is_relative_to(pathlib.Path(sys.prefix).resolve()), str(root)
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
for name, expected in manifest.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
entrypoints = {e.name:e.value for e in importlib.metadata.distribution('residual-agent-harness').entry_points if e.group == 'console_scripts'}
assert entrypoints['residual-station'] == 'residual.station.mission_server:main'
assert entrypoints['residual-mission-sync'] == 'residual.station.mission_client:main'
print(json.dumps({'installed_origin':str(root),'matched_files':len(manifest),'entrypoints':entrypoints}), flush=True)
print(json.dumps({'kernel_revision':authority_kernel.revision()}), flush=True)
''')
            env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME", "RESIDUAL_MISSION_CONFIG"}}
            env["MISSION_NODE_ADAPTER"] = str(adapter)
            for name, command in (
                ("installed-origin-kernel", [python, "-I", probe, manifest_path]),
                ("installed-station-help", [scripts / "residual-station", "--help"]),
                ("installed-mission-help", [scripts / "residual-mission-sync", "--help"]),
                ("installed-mission-tests", [python, "-I", test]),
            ):
                result = run(command, cwd=isolated, env=env)
                (output / (name + ".log")).write_text(result.stdout)
                report[name] = {"returncode": result.returncode}
                if result.returncode:
                    failures.append(name)
            if failures:
                raise RuntimeError("failed installed checks: " + ", ".join(failures))
            report["status"] = "PASS"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
