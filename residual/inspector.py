"""Read-only human inspection sidecar integration for px0.

px0 remains an external, untrusted observation surface. RESIDUAL binds an
inspection session to an exact Git HEAD/tree and records the px0 binary identity;
px0 never gains acceptance or integration authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .core import ContractError

PX0_VERSION = "0.1.2"
PX0_UPSTREAM_COMMIT = "57539720bad363980ef6dd80febbc925ffab214f"
PX0_REPOSITORY = "https://github.com/px0-ai/px0"


def _run(argv, *, cwd=None):
    proc = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode:
        raise ContractError("Inspector prerequisite command failed")
    return proc.stdout.strip()


def _spawn(argv, *, env):
    return subprocess.Popen(argv, env=env)


def _git(root: Path, *args: str) -> str:
    return _run(["git", "-c", "core.hooksPath=" + os.devnull, "-C", str(root), *args])


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass(frozen=True)
class InspectionSnapshot:
    workspace: str
    head_commit: str
    tree_hash: str
    clean: bool


@dataclass(frozen=True)
class InspectionReceipt:
    schema_version: int
    tool: str
    tool_version: str
    upstream_commit: str
    binary_sha256: str
    workspace: str
    head_commit: str
    tree_hash: str
    url: str
    lsp_enabled: bool
    telemetry_enabled: bool
    launched_at: str


def snapshot(workspace, *, require_clean: bool = True) -> InspectionSnapshot:
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ContractError("Inspector workspace must be an existing directory")
    head = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    clean = not bool(_git(root, "status", "--porcelain", "--untracked-files=all"))
    if require_clean and not clean:
        raise ContractError("Inspector requires a clean committed workspace so review binds to immutable Git state")
    return InspectionSnapshot(str(root), head, tree, clean)


def snapshot_is_current(value: InspectionSnapshot) -> bool:
    try:
        current = snapshot(value.workspace, require_clean=True)
    except (ContractError, OSError):
        return False
    return current.head_commit == value.head_commit and current.tree_hash == value.tree_hash


class Px0Inspector:
    def __init__(self, binary="px0", *, required_version: str = PX0_VERSION):
        resolved = shutil.which(str(binary)) if not Path(str(binary)).is_file() else str(Path(str(binary)).resolve())
        if not resolved:
            raise ContractError("px0 is not installed or was not found on PATH")
        self.binary = Path(resolved).resolve()
        self.required_version = required_version
        output = _run([str(self.binary), "-version"])
        expected = f"px0 {required_version} "
        if not output.startswith(expected):
            raise ContractError(f"Residual Inspector requires px0 {required_version}; found a different version")
        self.version_output = output
        self.binary_sha256 = _sha256(self.binary)

    def build_command(self, workspace, *, port: int, lsp: bool = False, open_browser: bool = True):
        if not (1 <= int(port) <= 65535):
            raise ContractError("Inspector port must be between 1 and 65535")
        command = [str(self.binary), "-host", "127.0.0.1", "-port", str(int(port)), "-no-telemetry", "-no-color"]
        if not lsp:
            command.append("-no-lsp")
        if not open_browser:
            command.append("-no-open")
        command.append(str(Path(workspace).expanduser().resolve()))
        return command

    def launch(self, workspace, *, port: int = 0, lsp: bool = False, open_browser: bool = True):
        bound = snapshot(workspace, require_clean=True)
        selected_port = int(port) if port else _free_port()
        command = self.build_command(bound.workspace, port=selected_port, lsp=lsp, open_browser=open_browser)
        env = {**os.environ, "DO_NOT_TRACK": "1", "PX0_TELEMETRY": "0"}
        process = _spawn(command, env=env)
        receipt = InspectionReceipt(
            schema_version=1,
            tool="px0",
            tool_version=self.required_version,
            upstream_commit=PX0_UPSTREAM_COMMIT,
            binary_sha256=self.binary_sha256,
            workspace=bound.workspace,
            head_commit=bound.head_commit,
            tree_hash=bound.tree_hash,
            url=f"http://127.0.0.1:{selected_port}",
            lsp_enabled=bool(lsp),
            telemetry_enabled=False,
            launched_at=datetime.now(timezone.utc).isoformat(),
        )
        return process, receipt, bound


def main(argv=None):
    parser = argparse.ArgumentParser(description="Launch the pinned px0 read-only inspection surface")
    parser.add_argument("workspace", nargs="?", default=".")
    parser.add_argument("--px0", default="px0", help="px0 binary path or executable name")
    parser.add_argument("--port", type=int, default=0, help="loopback port; 0 selects a free port")
    parser.add_argument("--lsp", action="store_true", help="allow local language-server processes (disabled by default)")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    parser.add_argument("--receipt", help="write the launch receipt as JSON")
    args = parser.parse_args(argv)
    try:
        inspector = Px0Inspector(args.px0)
        process, receipt, bound = inspector.launch(args.workspace, port=args.port, lsp=args.lsp, open_browser=not args.no_open)
        payload = asdict(receipt)
        if args.receipt:
            target = Path(args.receipt)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        try:
            code = process.wait()
        except KeyboardInterrupt:
            process.terminate()
            try:
                code = process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); code = process.wait()
        if not snapshot_is_current(bound):
            print("residual: inspector snapshot became stale during review", file=sys.stderr)
            return 3
        return int(code or 0)
    except (ContractError, OSError, ValueError) as exc:
        print(f"residual: inspector: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
