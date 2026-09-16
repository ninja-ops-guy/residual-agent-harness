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
import os
from pathlib import Path
import re
import stat
import time

from . import browser_build, browser_run
from .runner import MAX_REQUEST, read_json

MISSION_ID = re.compile(r"m-[0-9a-f]{32}\Z")
MODES = {"audit", "live", "build"}
READY = "RESIDUAL_WORKER_READY"
RUN_PREFIX = "RESIDUAL_WORKER_RUN_"
FATAL_PREFIX = "RESIDUAL_WORKER_FATAL_"
REJECTED = "RESIDUAL_WORKER_REJECTED:64"


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
    # guest-side directory view can lag briefly. Retry visibility only; the
    # authoritative workbench parser still validates the full request contract.
    deadline = time.monotonic() + 2.0
    while True:
        try:
            request = read_json(path, MAX_REQUEST)
            break
        except (FileNotFoundError, OSError, ValueError, TypeError, UnicodeError):
            if time.monotonic() >= deadline:
                raise ValueError("mission request not visible") from None
            time.sleep(0.05)
    if not isinstance(request, dict) or request.get("id") != mission_id or request.get("mode") != mode:
        raise ValueError("mission request identity mismatch")
    return path


def dispatch(mission_id: str, mode: str, *, mailbox: Path, root: Path, output_root: Path) -> int:
    request_path = _request(mailbox, mission_id, mode)
    common = [
        "--request", str(request_path),
        "--mailbox", str(mailbox),
        "--root", str(root),
        "--output-root", str(output_root),
        "--stream",
    ]
    if mode == "build":
        return int(browser_build.main(common) or 0)
    return int(browser_run.main(["run", *common]) or 0)


def _prepare_fifo(path: Path) -> None:
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISFIFO(info.st_mode):
            raise RuntimeError("worker control path is not a FIFO")
        path.unlink()
    os.mkfifo(path, 0o600)


def serve(*, fifo: Path, pid_file: Path, mailbox: Path, root: Path, output_root: Path) -> int:
    _prepare_fifo(fifo)
    pid_file.write_text(str(os.getpid()) + "\n", encoding="ascii")
    os.chmod(pid_file, 0o600)
    print(READY, flush=True)
    try:
        while True:
            # A shell builtin opens/writes/closes the FIFO once per mission.
            # Reopen after EOF so the worker process itself stays alive.
            with fifo.open("r", encoding="ascii", errors="strict") as stream:
                for line in stream:
                    try:
                        mission_id, mode = parse_command(line)
                    except (ValueError, UnicodeError):
                        print(REJECTED, flush=True)
                        continue
                    try:
                        status = dispatch(
                            mission_id, mode, mailbox=mailbox, root=root,
                            output_root=output_root,
                        )
                    except (OSError, ValueError, TypeError, KeyError):
                        # Request/transport admission failed before a trustworthy
                        # workbench result existed. Keep the worker alive and
                        # expose only a fixed status marker, never raw exception text.
                        status = 64
                    except BaseException:
                        # An unexpected exception inside this long-lived process
                        # may indicate interpreter corruption. Fail the worker
                        # closed instead of processing another mission in a
                        # potentially contaminated runtime.
                        print(f"{FATAL_PREFIX}{mission_id}:70", flush=True)
                        return 70
                    print(f"{RUN_PREFIX}{mission_id}:{status}", flush=True)
    finally:
        for path, require_fifo in ((fifo, True), (pid_file, False)):
            try:
                if not path.exists() and not path.is_symlink():
                    continue
                if require_fifo and not stat.S_ISFIFO(path.lstat().st_mode):
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
