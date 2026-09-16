"""Persistent Mission Control worker for the WebVM guest.

The browser VM has shown corruption after repeatedly starting and tearing down
CPython processes. Mission Control therefore starts this worker once and sends
only validated mission-id/mode pairs through a tiny DataDevice-backed regular
control record. Request bodies and provider responses continue to travel through
the existing DataDevice mailbox; all task, verifier, evidence and result-binding
logic remains authoritative in the existing workbench implementations.

The control record deliberately avoids FIFOs and other special-file primitives:
the production WebVM guest returns ENOSYS for ``mkfifo``. The host publishes the
record only after the request body has been awaited, and the worker consumes the
record before dispatch. A private busy marker fences page reload/reuse while a
mission is active.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import time

from residual.core import ContractError
from . import browser_build, browser_run
from .runner import MAX_REQUEST, read_json

MISSION_ID = re.compile(r"m-[0-9a-f]{32}\Z")
MODES = {"audit", "live", "build"}
READY = "RESIDUAL_WORKER_READY"
POISONED = "RESIDUAL_WORKER_POISONED"
RUN_PREFIX = "RESIDUAL_WORKER_RUN_"
FATAL_PREFIX = "RESIDUAL_WORKER_FATAL_"
REJECTED = "RESIDUAL_WORKER_REJECTED:64"
STOPPED = "RESIDUAL_WORKER_STOPPED"
SHUTDOWN = "shutdown"
CONTROL_NAME = "residual-worker.control"
MAX_CONTROL = 128


class RequestAdmissionError(ValueError):
    """Typed request/mailbox admission failure safe to report without reuse poison."""


def parse_command(line: str) -> tuple[str, str]:
    if not isinstance(line, str) or len(line) > 96:
        raise ValueError("invalid worker command")
    parts = line.strip().split(" ")
    if len(parts) != 2:
        raise ValueError("invalid worker command")
    mission_id, mode = parts
    if not MISSION_ID.fullmatch(mission_id) or mode not in MODES:
        raise ValueError("invalid worker command")
    return mission_id, mode


def _request(mailbox: Path, mission_id: str, mode: str) -> dict:
    path = mailbox / f"{mission_id}.json"
    # DataDevice.writeFile is awaited by the host before control publication, but
    # the guest-side directory view can lag briefly. Retry only failures expected
    # at this admission boundary. Do not absorb arbitrary TypeError/ValueError:
    # retained WebVM corruption has manifested as impossible Python constructor
    # return values, and those must poison the worker.
    deadline = time.monotonic() + 2.0
    while True:
        try:
            request = read_json(path, MAX_REQUEST)
            break
        except (OSError, UnicodeError, json.JSONDecodeError, ContractError):
            if time.monotonic() >= deadline:
                raise RequestAdmissionError("mission request not visible") from None
            time.sleep(0.05)
    if not isinstance(request, dict) or request.get("id") != mission_id or request.get("mode") != mode:
        raise RequestAdmissionError("mission request identity mismatch")
    return request


def dispatch(mission_id: str, mode: str, *, mailbox: Path, root: Path, output_root: Path) -> int:
    request = _request(mailbox, mission_id, mode)
    # Persistent execution deliberately bypasses the user-facing CLI main()
    # wrappers. Those wrappers translate broad Python exceptions (including
    # TypeError) into ordinary exit 1 for standalone usability. In a long-lived
    # interpreter, the same TypeError is a retained corruption signal and must
    # escape so serve() can poison the worker and require guest restart.
    if mode == "build":
        return int(browser_build.persistent_build(
            request=request,
            mailbox=mailbox,
            root=root,
            output_root=output_root,
        ) or 0)
    return int(browser_run.persistent_run(
        request=request,
        mailbox=mailbox,
        root=root,
        output_root=output_root,
    ) or 0)


def _dispatch_admitted(
    mission_id: str,
    mode: str,
    *,
    mailbox: Path,
    root: Path,
    output_root: Path,
) -> int:
    try:
        return dispatch(
            mission_id, mode, mailbox=mailbox, root=root, output_root=output_root
        )
    except RequestAdmissionError:
        return 64


def _owned_regular(path: Path) -> tuple[bool, os.stat_result | None]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False, None
    owned = not hasattr(os, "geteuid") or info.st_uid == os.geteuid()
    return stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and owned, info


def _write_private_file(path: Path, value: str, *, exclusive: bool = True) -> None:
    """Create one owner-private regular state file without following links."""
    flags = os.O_WRONLY | os.O_CREAT
    if exclusive:
        flags |= os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise RuntimeError(f"unsafe worker state path: {path.name}") from exc
    try:
        info = os.fstat(fd)
        owned = not hasattr(os, "geteuid") or info.st_uid == os.geteuid()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not owned:
            raise RuntimeError(f"unsafe worker state path: {path.name}")
        os.fchmod(fd, 0o600)
        if not exclusive:
            os.ftruncate(fd, 0)
        os.write(fd, value.encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_pid_file(path: Path) -> None:
    # Never follow a planted symlink or truncate a multiply-linked regular file.
    flags = os.O_WRONLY | os.O_CREAT
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise RuntimeError("worker pid path is unsafe") from exc
    try:
        info = os.fstat(fd)
        owned = not hasattr(os, "geteuid") or info.st_uid == os.geteuid()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not owned:
            raise RuntimeError("worker pid path is unsafe")
        os.fchmod(fd, 0o600)
        os.ftruncate(fd, 0)
        os.write(fd, (str(os.getpid()) + "\n").encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _is_poisoned(path: Path) -> bool:
    # Any existing node at the poison path is fail-closed. The host/worker writes
    # a private regular file, but an unexpected type never grants reuse authority.
    return path.exists() or path.is_symlink()


def _poison(path: Path, mission_id: str) -> None:
    if _is_poisoned(path):
        return
    _write_private_file(path, mission_id + "\n")


def _write_busy(path: Path, mission_id: str) -> None:
    _write_private_file(path, mission_id)


def _clear_exact_state(path: Path, expected: str) -> None:
    safe, info = _owned_regular(path)
    if not safe or info is None:
        if path.exists() or path.is_symlink():
            raise RuntimeError(f"unsafe worker state path: {path.name}")
        return
    if info.st_size != len(expected.encode("ascii")):
        raise RuntimeError(f"worker state identity mismatch: {path.name}")
    if path.read_text(encoding="ascii") != expected:
        raise RuntimeError(f"worker state identity mismatch: {path.name}")
    path.unlink()


def _consume_control(path: Path) -> str | tuple[str, str] | None:
    """Consume one complete regular control record, or return None while absent.

    DataDevice publication is awaited by the host. Requiring a trailing newline
    additionally prevents observing a mid-publication partial command as valid.
    """
    if not path.exists() and not path.is_symlink():
        return None
    safe, info = _owned_regular(path)
    if not safe or info is None:
        raise RuntimeError("worker control path is unsafe")
    if info.st_size > MAX_CONTROL:
        path.unlink()
        raise ValueError("invalid worker control record")
    try:
        raw = path.read_text(encoding="ascii")
    except UnicodeError as exc:
        path.unlink()
        raise ValueError("invalid worker control record") from exc
    if not raw.endswith("\n"):
        return None
    line = raw[:-1]
    if line == SHUTDOWN:
        path.unlink()
        return SHUTDOWN
    command = parse_command(line)
    path.unlink()
    return command


def serve(
    *,
    control_file: Path,
    pid_file: Path,
    mailbox: Path,
    root: Path,
    output_root: Path,
    poison_file: Path = Path("/tmp/residual-workbench.poison"),
    busy_file: Path = Path("/tmp/residual-workbench.busy"),
) -> int:
    # A timeout/corruption poison record outlives page/JS state and fences late
    # worker generations before they publish PID/READY.
    if _is_poisoned(poison_file):
        print(POISONED, flush=True)
        return 75
    # Never inherit stale control/busy state into a new trusted generation.
    if control_file.exists() or control_file.is_symlink() or busy_file.exists() or busy_file.is_symlink():
        print(POISONED, flush=True)
        return 75
    _write_pid_file(pid_file)
    try:
        if _is_poisoned(poison_file):
            print(POISONED, flush=True)
            return 75
        print(READY, flush=True)
        while True:
            try:
                command = _consume_control(control_file)
            except (ValueError, UnicodeError):
                print(REJECTED, flush=True)
                continue
            if command is None:
                time.sleep(0.05)
                continue
            if command == SHUTDOWN:
                print(STOPPED, flush=True)
                return 0
            mission_id, mode = command
            _write_busy(busy_file, mission_id)
            try:
                status = _dispatch_admitted(
                    mission_id, mode, mailbox=mailbox, root=root,
                    output_root=output_root,
                )
            except BaseException:
                # Poison from inside the worker before emitting the fatal marker.
                # This survives page loss and prevents a new generation from
                # silently starting after an impossible runtime failure.
                try:
                    _poison(poison_file, mission_id)
                finally:
                    print(f"{FATAL_PREFIX}{mission_id}:70", flush=True)
                return 70
            _clear_exact_state(busy_file, mission_id)
            print(f"{RUN_PREFIX}{mission_id}:{status}", flush=True)
    finally:
        # A stopped/dead worker cannot retain dispatch authority. Remove only safe
        # state nodes; poison is intentionally retained until explicit guest reset.
        for path in (control_file, pid_file, busy_file):
            try:
                if not path.exists() and not path.is_symlink():
                    continue
                safe, _ = _owned_regular(path)
                if not safe:
                    continue
                path.unlink()
            except OSError:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-file", type=Path, default=Path("/data") / CONTROL_NAME)
    parser.add_argument("--pid-file", type=Path, default=Path("/tmp/residual-workbench.pid"))
    parser.add_argument("--busy-file", type=Path, default=Path("/tmp/residual-workbench.busy"))
    parser.add_argument("--poison-file", type=Path, default=Path("/tmp/residual-workbench.poison"))
    parser.add_argument("--mailbox", type=Path, default=Path("/data"))
    parser.add_argument("--root", type=Path, default=Path("/opt/residual"))
    parser.add_argument("--output-root", type=Path, default=Path("/opt/residual/runs/missions"))
    args = parser.parse_args(argv)
    return serve(
        control_file=args.control_file,
        pid_file=args.pid_file,
        busy_file=args.busy_file,
        poison_file=args.poison_file,
        mailbox=args.mailbox,
        root=args.root,
        output_root=args.output_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
