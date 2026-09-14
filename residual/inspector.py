"""Read-only human inspection sidecar integration for px0.

px0 remains an external observation surface. RESIDUAL authenticates the
qualified release binary, launches it inside a fail-closed filesystem sandbox,
sanitizes its environment, binds review to an exact Git snapshot, and never
grants it acceptance or integration authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import selectors
import shutil
import subprocess
import sys
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .core import ContractError

PX0_VERSION = "0.1.2"
PX0_UPSTREAM_COMMIT = "343c14a705b3021bd18ee521c82f7d7227c4ee88"
PX0_REPOSITORY = "https://github.com/px0-ai/px0"

# SHA-256 digests published on the px0 v0.1.2 GitHub release. The CLI fails
# closed when the current platform has no qualified digest.
QUALIFIED_BINARY_SHA256 = {
    ("linux", "x86_64"): "c483293c67a63821712508931588d0495c336be5ace1e253b90624d3f5a06700",
    ("linux", "aarch64"): "55b3ea50813af24736ae641cd401e6cdd7e2e28f42f8d3685292a35b3b6e05a4",
    ("darwin", "x86_64"): "8a89c862e963acc361854a723028c0bfae1508665cf89cfe519da64746474f5b",
    ("darwin", "arm64"): "a760019629d62d7605f2ee59ac38b322059090c84756ac0f9898ff59677b7492",
    ("windows", "x86_64"): "7c09d17476f903f488be5539e854c424da7a8b8febbf0a37a847ff5b45ebda8f",
    ("windows", "arm64"): "07dbb53be8fa5cd529250b88c5df4993e5b9a5e67648446a5c9af16eec4e3fff",
}

_URL_RE = re.compile(r"http://127\.0\.0\.1:\d+")


def _run(argv, *, cwd=None):
    proc = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode:
        raise ContractError("Inspector prerequisite command failed")
    return proc.stdout.strip()


def _spawn(argv, *, env):
    return subprocess.Popen(
        argv,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


def _git(root: Path, *args: str) -> str:
    return _run(["git", "-c", "core.hooksPath=" + os.devnull, "-C", str(root), *args])


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _platform_key() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "arm64": "arm64" if system in {"darwin", "windows"} else "aarch64",
    }
    return system, aliases.get(machine, machine)


def _qualified_digest() -> str:
    key = _platform_key()
    digest = QUALIFIED_BINARY_SHA256.get(key)
    if not digest:
        raise ContractError(f"No qualified px0 {PX0_VERSION} binary digest is pinned for {key[0]}/{key[1]}")
    return digest


def _safe_env() -> dict[str, str]:
    # Do not inherit credentials, tokens, cloud configuration, proxy settings,
    # browser overrides, or arbitrary process state from the operator shell.
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "DO_NOT_TRACK": "1",
        "PX0_TELEMETRY": "0",
        # v0.1.2 performs a daily update check and has no disable flag. Point it
        # at loopback so the qualified build cannot make that outbound request.
        "PX0_UPDATE_URL": "http://127.0.0.1:9",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "127.0.0.1,localhost",
    }


def _git_paths(root: Path) -> list[Path]:
    paths = []
    for args in (("rev-parse", "--absolute-git-dir"), ("rev-parse", "--git-common-dir")):
        raw = _git(root, *args)
        value = Path(raw)
        if not value.is_absolute():
            value = (root / value).resolve()
        else:
            value = value.resolve()
        if value.exists() and value not in paths:
            paths.append(value)
    return paths


def _path_is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _masked_roots() -> list[Path]:
    roots = [Path("/tmp").resolve()]
    home = Path.home().resolve()
    if str(home) != "/" and home not in roots:
        roots.append(home)
    return roots


def _reexpose_readonly(command: list[str], source: Path, masked_root: Path) -> None:
    """Recreate a path hidden by tmpfs and bind only that path read-only."""
    source = source.resolve()
    if not _path_is_within(source, masked_root):
        return
    parents = []
    parent = source.parent
    while parent != masked_root and _path_is_within(parent, masked_root):
        parents.append(parent)
        parent = parent.parent
    for directory in reversed(parents):
        command.extend(["--dir", str(directory)])
    if source.is_dir():
        command.extend(["--dir", str(source)])
    command.extend(["--ro-bind", str(source), str(source)])


def _sandbox_command(binary: Path, workspace: Path, inner: list[str]) -> tuple[list[str], str]:
    if platform.system().lower() != "linux":
        raise ContractError(
            "Secure px0 inspection currently requires Linux bubblewrap; "
            "use --unsafe-no-sandbox only for non-authoritative local browsing"
        )
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise ContractError("Secure px0 inspection requires bubblewrap (bwrap) and refuses to launch without it")

    binary = binary.resolve()
    workspace = workspace.resolve()
    masked = _masked_roots()
    if any(_path_is_within(binary, root) for root in masked):
        raise ContractError(
            "Secure px0 inspection requires the qualified px0 binary to be installed outside "
            "the operator home and /tmp (for example /usr/local/bin/px0)"
        )

    mounts = [workspace, *_git_paths(workspace)]
    unique_mounts = []
    for path in mounts:
        path = path.resolve()
        # Git metadata already inside the reviewed workspace is covered by the
        # workspace bind; keep only external worktree/common-dir paths.
        if path != workspace and _path_is_within(path, workspace):
            continue
        if path not in unique_mounts:
            unique_mounts.append(path)

    command = [
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--unshare-uts",
        "--unshare-ipc",
        "--ro-bind", "/", "/",
    ]

    # Replace common secret-bearing writable locations with private tmpfs views.
    # Re-expose only the reviewed tree and any external Git metadata needed for
    # a linked worktree. This keeps /tmp and the operator home private even when
    # the candidate itself lives beneath one of those paths.
    for root in masked:
        command.extend(["--tmpfs", str(root)])
        for path in unique_mounts:
            _reexpose_readonly(command, path, root)

    command.extend(["--clearenv"])
    for key, value in _safe_env().items():
        command.extend(["--setenv", key, value])
    command.extend(inner)
    return command, "bubblewrap"


def _wait_for_url(process, *, timeout: float = 5.0) -> str:
    if process.stdout is None:
        raise ContractError("px0 stdout was not captured")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stderr = process.stderr.read().strip() if process.stderr else ""
                raise ContractError(f"px0 exited before publishing its URL{': ' + stderr if stderr else ''}")
            remaining = max(0.0, deadline - time.monotonic())
            if not selector.select(remaining):
                break
            line = process.stdout.readline()
            match = _URL_RE.search(line)
            if match:
                return match.group(0)
    finally:
        selector.close()
    raise ContractError("Timed out waiting for px0 to publish its bound loopback URL")


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
    binary_qualified: bool
    workspace: str
    head_commit: str
    tree_hash: str
    url: str
    lsp_enabled: bool
    telemetry_enabled: bool
    sandboxed: bool
    sandbox_backend: str
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


def validate_receipt_path(target, workspace) -> Path:
    destination = Path(target).expanduser().resolve()
    root = Path(workspace).expanduser().resolve()
    if _path_is_within(destination, root):
        raise ContractError(
            "Inspection receipts must be written outside the reviewed workspace "
            "so they cannot invalidate the bound snapshot"
        )
    return destination


class Px0Inspector:
    def __init__(self, binary="px0", *, required_version: str = PX0_VERSION, expected_binary_sha256: str | None = None):
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
        qualified = expected_binary_sha256 or _qualified_digest()
        if self.binary_sha256 != qualified:
            raise ContractError("px0 binary SHA-256 does not match the qualified upstream release artifact")

    def build_command(self, workspace, *, port: int = 0, lsp: bool = False, sandbox: bool = True):
        if not (0 <= int(port) <= 65535):
            raise ContractError("Inspector port must be between 0 and 65535")
        root = Path(workspace).expanduser().resolve()
        # Browser launch is intentionally owned by the parent process so px0 does
        # not need desktop/session environment access inside the sandbox.
        inner = [str(self.binary), "-host", "127.0.0.1", "-port", str(int(port)), "-no-color", "-no-open"]
        if not lsp:
            inner.append("-no-lsp")
        inner.append(str(root))
        if not sandbox:
            return inner, "none"
        return _sandbox_command(self.binary, root, inner)

    def launch(self, workspace, *, port: int = 0, lsp: bool = False, open_browser: bool = True, sandbox: bool = True):
        bound = snapshot(workspace, require_clean=True)
        command, backend = self.build_command(bound.workspace, port=port, lsp=lsp, sandbox=sandbox)
        process = _spawn(command, env=_safe_env())
        try:
            url = _wait_for_url(process)
        except Exception:
            process.terminate()
            raise
        if open_browser:
            webbrowser.open(url)
        receipt = InspectionReceipt(
            schema_version=2,
            tool="px0",
            tool_version=self.required_version,
            upstream_commit=PX0_UPSTREAM_COMMIT,
            binary_sha256=self.binary_sha256,
            binary_qualified=True,
            workspace=bound.workspace,
            head_commit=bound.head_commit,
            tree_hash=bound.tree_hash,
            url=url,
            lsp_enabled=bool(lsp),
            telemetry_enabled=False,
            sandboxed=bool(sandbox),
            sandbox_backend=backend,
            launched_at=datetime.now(timezone.utc).isoformat(),
        )
        return process, receipt, bound


def main(argv=None):
    parser = argparse.ArgumentParser(description="Launch authenticated px0 in a read-only inspection sandbox")
    parser.add_argument("workspace", nargs="?", default=".")
    parser.add_argument("--px0", default="px0", help="px0 binary path or executable name")
    parser.add_argument("--port", type=int, default=0, help="requested loopback port; 0 lets px0 atomically select one")
    parser.add_argument("--lsp", action="store_true", help="allow local language-server processes (disabled by default)")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    parser.add_argument("--receipt", help="write the launch receipt as JSON; path must be outside the reviewed workspace")
    parser.add_argument(
        "--unsafe-no-sandbox",
        action="store_true",
        help="disable OS sandboxing; resulting receipt is non-authoritative",
    )
    args = parser.parse_args(argv)
    try:
        bound_root = Path(args.workspace).expanduser().resolve()
        receipt_target = validate_receipt_path(args.receipt, bound_root) if args.receipt else None
        inspector = Px0Inspector(args.px0)
        sandboxed = not args.unsafe_no_sandbox
        process, receipt, bound = inspector.launch(
            bound_root,
            port=args.port,
            lsp=args.lsp,
            open_browser=not args.no_open,
            sandbox=sandboxed,
        )
        payload = asdict(receipt)
        if receipt_target:
            receipt_target.parent.mkdir(parents=True, exist_ok=True)
            receipt_target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        if not sandboxed:
            print("residual: WARNING: unsandboxed inspection is non-authoritative", file=sys.stderr)
        try:
            code = process.wait()
        except KeyboardInterrupt:
            process.terminate()
            try:
                code = process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait()
        if not snapshot_is_current(bound):
            print("residual: inspector snapshot became stale during review", file=sys.stderr)
            return 3
        return int(code or 0)
    except (ContractError, OSError, ValueError) as exc:
        print(f"residual: inspector: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
