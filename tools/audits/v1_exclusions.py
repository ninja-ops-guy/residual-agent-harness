#!/usr/bin/env python3
"""Bounded source-runtime audit; never a release or human-approval receipt."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import platform
import select
import subprocess
import sys
import tempfile
import threading
import time
from unittest import mock

PREFIX = "V1AUDIT:"
MARKER = "v1_audit_second_owner"


def emit(value):
    print(PREFIX + json.dumps(value, sort_keys=True), flush=True)


def no_external_effects(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"}:
        raise PermissionError("audit forbids external connection or process launch")
    if event == "socket.bind":
        address = args[1]
        if not isinstance(address, tuple) or not ipaddress.ip_address(address[0]).is_loopback:
            raise PermissionError("audit forbids non-loopback binding")


def child(repo: Path, root: Path, role: str):
    sys.path.insert(0, str(repo))
    sys.addaudithook(no_external_effects)
    server = thread = None
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from residual.station.service import Station
            from residual.station.server import Server
            station = Station(str(root))
            if role == "second":
                station.store.settings({MARKER: "synthetic-second-owner"})
            server = Server(("127.0.0.1", 0), station)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
        emit({"status": "READY", "pid": os.getpid(), "role": role,
              "root": str(station.store.root), "port": server.server_port})
        sys.stdin.readline()
        observed = station.store.settings().get(MARKER)
        emit({"status": "OBSERVED", "second_marker_visible": observed == "synthetic-second-owner"})
        return 0
    except Exception as error:
        # Only synthetic checkout/temp-directory operations occur in this process.
        message = str(error).lower()
        explicit = type(error).__name__ in {"ContractError", "RuntimeError", "PermissionError"} and any(
            token in message for token in ("already running", "another station", "owner", "in use", "locked"))
        emit({"status": "REJECTED" if explicit else "BLOCKED", "error_type": type(error).__name__})
        return 2
    finally:
        if server is not None:
            if thread is not None:
                server.shutdown()
            server.server_close()


def records(text):
    return [json.loads(line[len(PREFIX):]) for line in text.splitlines() if line.startswith(PREFIX)]


def environment(home):
    result = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "LANG", "LC_ALL") if key in os.environ}
    result.update(HOME=str(home), USERPROFILE=str(home), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
    return result


def spawn(repo, root, role, home):
    return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--repo", str(repo),
                             "--child", str(root), "--role", role], cwd=repo, env=environment(home),
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def ready(process, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        readable, _, _ = select.select([process.stdout], [], [], max(0, deadline - time.monotonic()))
        if not readable:
            break
        line = process.stdout.readline()
        if not line:
            break
        parsed = records(line)
        if parsed:
            return parsed[0]
    raise TimeoutError("no bounded child readiness result")


def finish(process):
    try:
        out, _ = process.communicate("observe\n", timeout=10)
        return records(out)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)


def ownership(repo, same_directory):
    with tempfile.TemporaryDirectory(prefix="residual-v1-audit-") as temporary:
        temp = Path(temporary)
        first = second = None
        try:
            first = spawn(repo, temp / "first", "first", temp)
            a = ready(first)
            if a["status"] != "READY":
                return {"status": "BLOCKED", "first": a}
            second = spawn(repo, temp / ("first" if same_directory else "second"), "second", temp)
            b = ready(second)
            concurrent = first.poll() is None and second.poll() is None
            finish(second)
            observed = finish(first)
            shared = any(item.get("second_marker_visible") for item in observed)
            if same_directory:
                status = "FAIL" if b["status"] == "READY" and concurrent and shared else (
                    "PASS" if b["status"] == "REJECTED" and not shared else "BLOCKED")
            else:
                status = "PASS" if b["status"] == "READY" and concurrent and not shared else "BLOCKED"
            return {"status": status, "first": a, "second": b, "simultaneous_lifetime": concurrent,
                    "first_observed_second_write": shared}
        except Exception as error:
            return {"status": "BLOCKED", "error_type": type(error).__name__}
        finally:
            for process in (second, first):
                if process is not None and process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)


class BindReached(Exception):
    pass


def policy_exit_is_rejection(use_cli, code, attempts, diagnostic):
    return (use_cli and type(code) is int and code == 2 and not attempts
            and "Non-loopback Station exposure" in diagnostic)


def bind_policy(repo, host, use_cli=False, configured=False):
    sys.path.insert(0, str(repo))
    from http.server import ThreadingHTTPServer
    from residual.core import ContractError
    from residual.station import server as app
    from residual.station.service import Station
    attempts = []
    diagnostic = io.StringIO()
    def intercepted(instance):
        attempts.append(list(instance.server_address))
        raise BindReached("intercepted before OS bind")
    with tempfile.TemporaryDirectory(prefix="residual-v1-bind-audit-") as temporary:
        env = environment(temporary)
        if configured:
            env.update(RESIDUAL_REMOTE_EXPOSURE="1", RESIDUAL_ALLOWED_HOSTS="example.invalid",
                       RESIDUAL_PUBLIC_URL="https://example.invalid")
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(ThreadingHTTPServer, "server_bind", intercepted):
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(diagnostic):
                    if use_cli:
                        app.main(["--host", host, "--port", "0", "--data", temporary])
                    else:
                        service = app.Server((host, 0), Station(temporary))
                        service.server_close()
            except SystemExit as error:
                if policy_exit_is_rejection(use_cli, error.code, attempts, diagnostic.getvalue()):
                    result = "REJECTED_BEFORE_BIND"
                else:
                    return {"status": "BLOCKED", "error_type": "SystemExit", "bind_attempts": attempts}
            except BindReached:
                result = "REACHED_BIND"
            except (ContractError, PermissionError, ValueError) as error:
                result = "REJECTED_BEFORE_BIND" if not attempts else "BLOCKED"
                rejection = type(error).__name__
            except Exception as error:
                return {"status": "BLOCKED", "error_type": type(error).__name__}
            else:
                return {"status": "BLOCKED", "reason": "no terminal policy observation", "bind_attempts": attempts}
    if configured:
        status = "OBSERVED_NOT_GATED"
    elif host == "127.0.0.1":
        status = "PASS" if result == "REACHED_BIND" else "BLOCKED"
    else:
        status = "PASS" if result == "REJECTED_BEFORE_BIND" else "FAIL"
    return {"status": status, "result": result, "bind_attempts": attempts,
            "scope": "policy before intercepted OS bind; no non-loopback listener"}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, timeout=10).strip()


def identity(repo, expected):
    head = git(repo, "rev-parse", "HEAD")
    if head != expected or git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("wrong or dirty source checkout")
    blobs = {}
    for name in ("service.py", "server.py", "store.py", "worker.py"):
        relative = "residual/station/" + name
        data = (repo / relative).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if git(repo, "rev-parse", "HEAD:" + relative) != blob:
            raise ValueError("working source differs from Git blob")
        blobs[relative] = {"git_blob": blob, "sha256": hashlib.sha256(data).hexdigest()}
    return {"head": head, "tree": git(repo, "rev-parse", "HEAD^{tree}"), "files": blobs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--child", type=Path)
    parser.add_argument("--role", choices=("first", "second"), default="first")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.child:
        return child(repo, args.child, args.role)
    if not args.expected_head or not args.output:
        parser.error("--expected-head and --output are required for audit")
    result = {"schema": "residual.v1-exclusion-audit.v1", "execution": "DISPOSABLE_RUNTIME_AND_BIND_INTERCEPTION",
              "release_qualification": False, "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "python": platform.python_version(), "platform": platform.platform(), "cases": {}}
    try:
        result["source"] = identity(repo, args.expected_head)
        # These create only bounded Python children and loopback-only temporary services.
        result["cases"]["separate_data_directories_positive"] = ownership(repo, False)
        result["cases"]["CV-06_same_data_directory_second_owner"] = ownership(repo, True)
        sys.addaudithook(no_external_effects)
        for case, host, cli, configured in (
            ("loopback_policy_positive", "127.0.0.1", False, False),
            ("loopback_cli_positive", "127.0.0.1", True, False),
            ("CV-03_constructor_nonloopback_default", "0.0.0.0", False, False),
            ("CV-03_cli_nonloopback_default", "0.0.0.0", True, False),
            ("nonloopback_explicit_optin_observation", "0.0.0.0", False, True)):
            try:
                result["cases"][case] = bind_policy(repo, host, cli, configured)
            except Exception as error:
                result["cases"][case] = {"status": "BLOCKED", "error_type": type(error).__name__}
        source = (repo / "residual/station/worker.py").read_text(encoding="utf-8")
        result["cases"]["CV-09_shared_comms_recovery_and_exclusion"] = {
            "status": "BLOCKED", "reason": "requires approved inclusion/exclusion and selected Shared Comms source; no full feature-exclusion claim",
            "recover_comms_name_in_worker_source": "recover_comms" in source,
            "outbox_name_in_worker_source": "outbox" in source.lower()}
        statuses = [case["status"] for case in result["cases"].values()]
        result["status"] = "FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "PASS"
    except Exception as error:
        result.update(status="BLOCKED", error_type=type(error).__name__)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(result, destination, sort_keys=True, indent=2)
        destination.write("\n")
    emit(result)
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
