"""Persistent Mission Control worker for the WebVM guest.

The browser VM has shown corruption after repeatedly starting and tearing down
CPython processes. Mission Control therefore starts this worker once and sends
only validated mission-id/mode pairs over a private FIFO. Request bodies and
provider responses continue to travel through the existing DataDevice mailbox;
all task, verifier, evidence and result-binding logic remains authoritative in
the existing workbench implementations.
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
RUN_PREFIX = "RESIDUAL_WORKER_RUN_"
FATAL_PREFIX = "RESIDUAL_WORKER_FATAL_"
REJECTED = "RESIDUAL_WORKER_REJECTED:64"
STOPPED = "RESIDUAL_WORKER_STOPPED"
SHUTDOWN = "shutdown"


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


def _request(mailbox: Path, mission_id: str, mode: str):
    path = mailbox / f"{mission_id}.json"
    # DataDevice.writeFile is awaited by the host before FIFO dispatch, but the
    # guest-side directory view can lag briefly. Retry only failures that are
    # explicitly expected at this admission boundary. Do not absorb arbitrary
    # TypeError/ValueError: retained WebVM corruption has manifested as impossible
    # Python constructor return values, and those must poison the worker.
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
    return path


def dispatch(mission_id: str, mode: str, *, mailbox: Path, root: Path, output_root: Path) -> int:
    request_path = _request(mailbox, mission_id, mode)
    # Persistent execution deliberately bypasses the user-facing CLI main()
    # wrappers. Those wrappers translate broad Python exceptions (including
    # TypeError) into ordinary exit 1 for standalone usability. In a long-lived
    # interpreter, the same TypeError is a retained corruption signal and must
    # escape so serve() can poison the worker and require guest restart.
    if mode == "build":
        return int(browser_build.persistent_build(
            request_path=request_path,
            mailbox=mailbox,
            root=root,
            output_root=output_root,
        ) or 0)
    return int(browser_run.persistent_run(
        request_path=request_path,
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
        # A typed mailbox/request admission failure is bounded and does not imply
        # that the persistent interpreter itself is suspect.
        return 64


def _prepare_fifo(path: Path) -> None:
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISFIFO(info.st_mode):
            raise RuntimeError("worker control path is not a FIFO")
        path.unlink()
    os.mkfifo(path, 0o600)


def _write_pid_file(path: Path) -> None:
    # Never follow a planted symlink or truncate a multiply-linked regular file.
    # Open without O_TRUNC, validate the opened inode, then truncate/write it.
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


def serve(*, fifo: Path, pid_file: Path, mailbox: Path, root: Path, output_root: Path) -> int:
    _prepare_fifo(fifo)
    _write_pid_file(pid_file)
    print(READY, flush=True)
    try:
        while True:
            # A shell builtin opens/writes/closes the FIFO once per request.
            # Reopen after EOF so the worker process itself stays alive.
            with fifo.open("r", encoding="ascii", errors="strict") as stream:
                for line in stream:
                    if line.strip() == SHUTDOWN:
                        print(STOPPED, flush=True)
                        return 0
                    try:
                        mission_id, mode = parse_command(line)
                    except (ValueError, UnicodeError):
                        print(REJECTED, flush=True)
                        continue
                    try:
                        status = _dispatch_admitted(
                            mission_id, mode, mailbox=mailbox, root=root,
                            output_root=output_root,
                        )
                    except BaseException:
                        # Any exception that escaped typed request admission and
                        # the persistent workbench contract is unexpected in a
                        # long-lived interpreter. Fail closed and require restart.
                        print(f"{FATAL_PREFIX}{mission_id}:70", flush=True)
                        return 70
                    print(f"{RUN_PREFIX}{mission_id}:{status}", flush=True)
    finally:
        for path, require_fifo in ((fifo, True), (pid_file, False)):
            try:
                if not path.exists() and not path.is_symlink():
                    continue
                info = path.lstat()
                if require_fifo and not stat.S_ISFIFO(info.st_mode):
                    continue
                if not require_fifo and not stat.S_ISREG(info.st_mode):
                    continue
                path.unlink()
            except OSError:
                pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fifo", type=Path, default=Path("/tmp/residual-workbench.fifo"))
    parser.add_argument("--pid-file", type=Path, default=Path("/tmp/residual-workbench.pid"))
    parser.add_argument("--mailbox", type=Path, default=Path("/data"))
    parser.add_argument("--root", type=Path, default=Path("/opt/residual"))
    parser.add_argument("--output-root", type=Path, default=Path("/opt/residual/runs/missions"))
    args = parser.parse_args(argv)
    return serve(
        fifo=args.fifo, pid_file=args.pid_file, mailbox=args.mailbox,
        root=args.root, output_root=args.output_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
