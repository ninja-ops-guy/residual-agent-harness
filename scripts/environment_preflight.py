#!/usr/bin/env python3
"""Machine-readable capability preflight for broad RESIDUAL qualification.

ENV-G01 fails closed before the broad suite when a mandatory runner capability is
missing.  It performs no external network access and records only an allowlisted
set of environment variables so CI evidence cannot accidentally capture secrets.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import signal
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "residual.environment-preflight.v1"
SAFE_ENV_KEYS = ("CI", "GITHUB_ACTIONS", "RUNNER_OS", "RUNNER_ARCH")
REQUIRED_DISTRIBUTIONS = ("cryptography", "PyYAML", "hypothesis", "coverage", "pytest")


def _result(name: str, passed: bool, detail: str, **evidence: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": name,
        "required": True,
        "status": "PASS" if passed else "BLOCKED",
        "detail": detail,
    }
    if evidence:
        out["evidence"] = evidence
    return out


def _git_identity() -> dict[str, Any]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        ok = len(head) == 40 and len(tree) == 40
        return _result("git_identity", ok, "exact HEAD/tree recorded" if ok else "invalid HEAD/tree form", head=head, tree=tree)
    except (OSError, subprocess.SubprocessError) as exc:
        return _result("git_identity", False, f"unable to record git identity: {type(exc).__name__}")


def _python_runtime() -> dict[str, Any]:
    ok = sys.version_info >= (3, 11) and platform.system() == "Linux"
    return _result(
        "python_linux_runtime",
        ok,
        "CPython >=3.11 on Linux" if ok else "broad-suite reference runtime requires Python >=3.11 on Linux",
        python=platform.python_version(),
        implementation=platform.python_implementation(),
        platform=platform.platform(),
    )


def _dependencies() -> dict[str, Any]:
    versions: dict[str, str | None] = {}
    missing: list[str] = []
    for dist in REQUIRED_DISTRIBUTIONS:
        try:
            versions[dist] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            versions[dist] = None
            missing.append(dist)
    return _result(
        "qualification_dependencies",
        not missing,
        "required factory/qualification distributions present" if not missing else "missing: " + ", ".join(missing),
        versions=versions,
    )


def _loopback() -> dict[str, Any]:
    listener: socket.socket | None = None
    client: socket.socket | None = None
    accepted: socket.socket | None = None
    try:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.settimeout(2.0)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2.0)
        client.connect(("127.0.0.1", port))
        accepted, _ = listener.accept()
        return _result("loopback_socket", True, "AF_INET loopback bind/connect/accept succeeded")
    except OSError as exc:
        return _result("loopback_socket", False, f"loopback unavailable: {exc.__class__.__name__}: {exc}")
    finally:
        for sock in (accepted, client, listener):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass


def _bubblewrap() -> dict[str, Any]:
    binary = shutil.which("bwrap")
    if not binary:
        return _result("bubblewrap_namespace", False, "bwrap executable not found")
    cmd = [
        binary,
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--unshare-net",
        "--ro-bind",
        "/",
        "/",
        "--",
        "/bin/true",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return _result("bubblewrap_namespace", False, f"bwrap preflight failed to execute: {type(exc).__name__}", executable=binary)
    detail = "bubblewrap PID/network namespace preflight passed" if proc.returncode == 0 else f"bwrap preflight exit={proc.returncode}"
    return _result("bubblewrap_namespace", proc.returncode == 0, detail, executable=binary, returncode=proc.returncode)


def _subprocess_and_signal() -> dict[str, Any]:
    proc: subprocess.Popen[str] | None = None
    try:
        basic = subprocess.run(
            [sys.executable, "-c", "print('ENV_G01_SUBPROCESS_OK')"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if basic.stdout.strip() != "ENV_G01_SUBPROCESS_OK":
            return _result("subprocess_signal", False, "subprocess output mismatch")
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        proc.send_signal(signal.SIGTERM)
        rc = proc.wait(timeout=5)
        return _result("subprocess_signal", rc != 0, "subprocess creation and SIGTERM delivery succeeded" if rc != 0 else "child ignored SIGTERM", returncode=rc)
    except (OSError, subprocess.SubprocessError) as exc:
        return _result("subprocess_signal", False, f"subprocess/signal check failed: {type(exc).__name__}: {exc}")
    finally:
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                proc.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                pass


def _sqlite_wal_lock() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="residual-env-g01-sqlite-") as td:
        path = Path(td) / "preflight.sqlite3"
        first: sqlite3.Connection | None = None
        second: sqlite3.Connection | None = None
        try:
            first = sqlite3.connect(path, timeout=0.1)
            mode = first.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            first.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT)")
            first.commit()
            first.execute("BEGIN IMMEDIATE")
            second = sqlite3.connect(path, timeout=0.05)
            locked = False
            try:
                second.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                locked = "locked" in str(exc).lower()
            finally:
                try:
                    second.rollback()
                except sqlite3.Error:
                    pass
            ok = str(mode).lower() == "wal" and locked
            return _result(
                "sqlite_wal_lock",
                ok,
                "SQLite WAL and write-lock contention semantics available" if ok else "SQLite WAL or lock contention semantics unavailable",
                sqlite_version=sqlite3.sqlite_version,
                journal_mode=str(mode),
                contention_locked=locked,
            )
        except sqlite3.Error as exc:
            return _result("sqlite_wal_lock", False, f"SQLite capability failed: {exc.__class__.__name__}: {exc}", sqlite_version=sqlite3.sqlite_version)
        finally:
            if first is not None:
                try:
                    first.rollback()
                    first.close()
                except sqlite3.Error:
                    pass
            if second is not None:
                try:
                    second.close()
                except sqlite3.Error:
                    pass


def _clock() -> dict[str, Any]:
    a = time.monotonic_ns()
    time.sleep(0.001)
    b = time.monotonic_ns()
    return _result("monotonic_clock", b > a, "monotonic clock advanced" if b > a else "monotonic clock did not advance", delta_ns=b - a)


def _writable_executable_storage() -> dict[str, Any]:
    try:
        with tempfile.TemporaryDirectory(prefix="residual-env-g01-fs-") as td:
            root = Path(td)
            data = root / "probe.txt"
            data.write_text("ENV_G01_WRITE_OK\n", encoding="utf-8")
            if data.read_text(encoding="utf-8") != "ENV_G01_WRITE_OK\n":
                return _result("writable_executable_storage", False, "temporary file round trip failed", root=str(root))
            script = root / "probe.sh"
            script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            script.chmod(0o700)
            proc = subprocess.run([str(script)], capture_output=True, text=True, timeout=5)
            ok = proc.returncode == 0
            return _result("writable_executable_storage", ok, "temporary storage is writable and executable" if ok else f"direct executable probe exit={proc.returncode}")
    except (OSError, subprocess.SubprocessError) as exc:
        return _result("writable_executable_storage", False, f"storage capability failed: {type(exc).__name__}: {exc}")


def safe_environment() -> dict[str, str]:
    return {key: os.environ[key] for key in SAFE_ENV_KEYS if key in os.environ}


def overall_status(checks: list[dict[str, Any]]) -> str:
    return "PASS" if checks and all((not item.get("required")) or item.get("status") == "PASS" for item in checks) else "BLOCKED"


def run_checks() -> list[dict[str, Any]]:
    checks: tuple[Callable[[], dict[str, Any]], ...] = (
        _git_identity,
        _python_runtime,
        _dependencies,
        _loopback,
        _bubblewrap,
        _subprocess_and_signal,
        _sqlite_wal_lock,
        _clock,
        _writable_executable_storage,
    )
    return [check() for check in checks]


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": overall_status(checks),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "sqlite": sqlite3.sqlite_version,
            "openssl": ssl.OPENSSL_VERSION,
        },
        "environment": safe_environment(),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed RESIDUAL broad-suite environment preflight")
    parser.add_argument("--output", type=Path, required=True, help="machine-readable JSON evidence path")
    args = parser.parse_args()

    report = build_report(run_checks())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ENV-G01 {report['status']}: {args.output}")
    if report["status"] != "PASS":
        for item in report["checks"]:
            if item.get("required") and item.get("status") != "PASS":
                print(f"BLOCKED {item['name']}: {item['detail']}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
