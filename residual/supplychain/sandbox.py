"""Third-party module sandboxing. Implements ENT5-R7.

Third-party modules MUST run in isolated containers with: no network
access to the host, filesystem access limited to explicit allowlists,
non-root execution, and resource constraints. :class:`SandboxPolicy`
models the container policy; :func:`validate_manifest` enforces it;
:func:`run_sandboxed` executes third-party Python only behind a
kernel-enforced sandbox boundary and fails closed when that boundary is
unavailable.
"""
from __future__ import annotations

import json
import os
import posixpath
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable

from residual.core import ContractError, identifier

def _check_allowlist_path(path: str) -> None:
    if not isinstance(path, str) or not path.startswith("/"):
        raise ContractError(f"filesystem allowlist path must be absolute: {path!r}")
    if ".." in path.split("/"):
        raise ContractError(f"filesystem allowlist path must not contain '..': {path!r}")


@dataclass(frozen=True)
class SandboxPolicy:
    """Container isolation policy. Implements ENT5-R7.

    Defaults match the spec: no host network, filesystem allowlist,
    non-root user, and resource limits.
    """

    allow_network: bool = False
    filesystem_allowlist: tuple[str, ...] = ()
    run_as_user: str = "sandbox"
    run_as_root: bool = False
    max_memory_mb: int = 256
    max_cpu_seconds: int = 60

    def __post_init__(self):
        if type(self.allow_network) is not bool or type(self.run_as_root) is not bool:
            raise ContractError("policy flags must be bool")
        for path in self.filesystem_allowlist:
            _check_allowlist_path(path)
        if self.run_as_root:
            raise ContractError("ENT5-R7: containers MUST run as non-root")
        if not isinstance(self.run_as_user, str) or not self.run_as_user:
            raise ContractError("run_as_user required")
        if self.run_as_user in ("root", "0"):
            raise ContractError("ENT5-R7: containers MUST run as non-root")
        if type(self.max_memory_mb) is not int or self.max_memory_mb < 1:
            raise ContractError("max_memory_mb must be a positive int")
        if type(self.max_cpu_seconds) is not int or self.max_cpu_seconds < 1:
            raise ContractError("max_cpu_seconds must be a positive int")

    def path_allowed(self, path: str) -> bool:
        """True if ``path`` is inside the filesystem allowlist. Implements ENT5-R7."""
        normalized = posixpath.normpath(path)
        if normalized.startswith("..") or ".." in normalized.split("/"):
            return False
        for allowed in self.filesystem_allowlist:
            allowed = posixpath.normpath(allowed)
            if normalized == allowed or normalized.startswith(allowed.rstrip("/") + "/"):
                return True
        return False


@dataclass(frozen=True)
class ModuleManifest:
    """Manifest declaring a third-party module's sandbox policy. Implements ENT5-R7."""

    name: str
    version: str
    policy: SandboxPolicy

    def __post_init__(self):
        identifier(self.name)
        if not isinstance(self.version, str) or not self.version:
            raise ContractError("module version required")
        if not isinstance(self.policy, SandboxPolicy):
            raise ContractError("policy must be a SandboxPolicy")


def validate_manifest(manifest: ModuleManifest) -> None:
    """Validate a module manifest against ENT5-R7 requirements.

    Raises ContractError if the manifest requests host network access,
    root execution, or an invalid policy.
    """
    if not isinstance(manifest, ModuleManifest):
        raise ContractError("manifest must be a ModuleManifest")
    if manifest.policy.allow_network:
        raise ContractError("ENT5-R7: containers MUST have no network access to the host")


_RESULT_PREFIX = "RESIDUAL_SANDBOX_RESULT:"
_MAX_RESULT_BYTES = 1 << 20

# This wrapper is executed only inside a kernel-isolated sandbox selected by
# residual.sandbox. Keeping arbitrary module source out of the parent process
# removes the previous Python-object-model escape from the host trust boundary.
_ISOLATED_RUNNER = r"""
import contextlib
import io
import json
import sys

PREFIX = "RESIDUAL_SANDBOX_RESULT:"
capture = io.StringIO()
try:
    envelope = json.loads(sys.stdin.read())
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"source", "function", "args", "kwargs"}
        or not isinstance(envelope["source"], str)
        or not isinstance(envelope["function"], str)
        or not isinstance(envelope["args"], list)
        or not isinstance(envelope["kwargs"], dict)
    ):
        raise ValueError("invalid envelope")
    namespace = {"__name__": "__residual_sandboxed_module__"}
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        # Deliberately dynamic: this interpreter is already inside a kernel
        # mount/network/PID/resource sandbox. The host process never executes
        # untrusted Python source.
        exec(compile(envelope["source"], "<residual-supplychain-module>", "exec"),
             namespace, namespace)
        function = namespace.get(envelope["function"])
        if not callable(function):
            raise ValueError("entrypoint missing")
        value = function(*envelope["args"], **envelope["kwargs"])
    payload = json.dumps({"ok": True, "value": value},
                         separators=(",", ":"), allow_nan=False)
except BaseException:
    payload = json.dumps({"ok": False, "error": "sandboxed_module_failed"},
                         separators=(",", ":"))
sys.__stdout__.write(PREFIX + payload + "\n")
"""


def _kernel_execute(
    manifest: ModuleManifest,
    source: str,
    function: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    read_file_bytes: Callable[[str], bytes] | None,
) -> Any:
    """Execute third-party Python only behind kernel-enforced containment."""
    validate_manifest(manifest)
    if sys.platform != "linux":
        raise ContractError("ENT5-R7: kernel sandbox execution requires Linux")
    if os.geteuid() == 0:
        raise ContractError("ENT5-R7: refuse third-party execution from a root parent")
    if read_file_bytes is not None:
        raise ContractError(
            "ENT5-R7: host callback filesystem emulation is disabled; "
            "materialize reviewed files and allowlist their real paths"
        )
    if not isinstance(source, str) or len(source.encode("utf-8")) > 512_000:
        raise ContractError("ENT5-R7: module source exceeds 512 KB")
    if not isinstance(function, str) or not function:
        raise ContractError("ENT5-R7: sandbox entrypoint required")
    try:
        envelope = json.dumps(
            {"source": source, "function": function, "args": list(args), "kwargs": kwargs},
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        raise ContractError("ENT5-R7: sandbox arguments must be JSON-serializable") from None
    if len(envelope.encode("utf-8")) > 1_000_000:
        raise ContractError("ENT5-R7: sandbox request exceeds 1 MB")

    from residual.sandbox import (
        FsAllowlist,
        NetworkPolicy,
        SandboxLimits,
        SandboxSpec,
        select_backend,
    )

    resolved: list[str] = []
    for raw in manifest.policy.filesystem_allowlist:
        path = Path(raw)
        if not path.exists():
            raise ContractError(f"ENT5-R7: allowlisted path does not exist: {raw!r}")
        value = str(path.resolve())
        if value != raw.rstrip("/") and value != raw:
            raise ContractError(
                f"ENT5-R7: allowlisted path must be canonical before execution: {raw!r}"
            )
        resolved.append(value)

    spec = SandboxSpec(
        name="supplychain",
        limits=SandboxLimits(
            cpu_seconds=manifest.policy.max_cpu_seconds,
            memory_mb=manifest.policy.max_memory_mb,
            max_pids=16,
            timeout_seconds=manifest.policy.max_cpu_seconds + 5,
            max_output_bytes=_MAX_RESULT_BYTES,
        ),
        fs=FsAllowlist(read=tuple(resolved)),
        network=NetworkPolicy.DENY,
        workdir="/",
    )
    backend = select_backend(require_kernel=True)
    backend.start(spec)
    try:
        result = backend.exec(
            [sys.executable, "-I", "-S", "-c", _ISOLATED_RUNNER],
            stdin=envelope,
        )
    finally:
        backend.stop()

    if result.enforcement != "kernel":
        raise ContractError("ENT5-R7: kernel isolation was not actually enforced")
    if not result.ok:
        raise ContractError(
            "ENT5-R7: sandboxed module was stopped by the containment boundary"
        )

    encoded = result.stdout.encode("utf-8", "replace")
    if len(encoded) > _MAX_RESULT_BYTES:
        raise ContractError("ENT5-R7: sandbox result exceeds output budget")
    payload = None
    for line in reversed(result.stdout.splitlines()):
        if line.startswith(_RESULT_PREFIX):
            payload = line[len(_RESULT_PREFIX):]
            break
    if payload is None:
        raise ContractError("ENT5-R7: sandbox returned no result frame")
    try:
        decoded = json.loads(payload)
    except (json.JSONDecodeError, RecursionError):
        raise ContractError("ENT5-R7: sandbox returned malformed result") from None
    if not isinstance(decoded, dict) or decoded.get("ok") is not True or set(decoded) != {"ok", "value"}:
        raise ContractError("ENT5-R7: sandboxed module failed")
    return decoded["value"]


def compile_sandboxed(manifest: ModuleManifest, source: str, function: str) -> Callable[..., Any]:
    """Prepare a callable whose executions occur only under kernel isolation. Implements ENT5-R7."""
    validate_manifest(manifest)

    def isolated_callable(*args: Any, **kwargs: Any) -> Any:
        return _kernel_execute(
            manifest, source, function, args, kwargs, read_file_bytes=None
        )

    return isolated_callable


def run_sandboxed(
    manifest: ModuleManifest,
    source: str,
    function: str,
    *args: Any,
    read_file_bytes: Callable[[str], bytes] | None = None,
    **kwargs: Any,
) -> Any:
    """Run a third-party module only in a kernel-enforced sandbox. Implements ENT5-R7.

    The former in-process dynamic execution path has been removed. Arbitrary
    Python now executes in the strongest residual.sandbox backend with kernel
    isolation required, network denied, a read-only real-path allowlist,
    non-root parent enforcement, and bounded CPU/memory/PID/wall/output
    resources. If those guarantees are unavailable the call fails closed.
    """
    return _kernel_execute(
        manifest, source, function, args, kwargs, read_file_bytes=read_file_bytes
    )
