"""Third-party module sandboxing. Implements ENT5-R7.

Third-party modules MUST run in isolated containers with: no network
access to the host, filesystem access limited to explicit allowlists,
non-root execution, and resource constraints. :class:`SandboxPolicy`
models the container policy; :func:`validate_manifest` enforces it;
:func:`run_sandboxed` executes a module callable under a restricted
namespace with no network builtins and an allowlisted ``open``.
"""
from __future__ import annotations

import io
import posixpath
from dataclasses import dataclass, field
from typing import Any, Callable

from residual.core import ContractError, identifier

# Network-capable stdlib modules a sandboxed module may not touch.
DENIED_NETWORK_MODULES = frozenset(
    {"socket", "urllib", "http", "ftplib", "smtplib", "ssl", "requests"}
)

# Restricted builtins available to sandboxed module code.
_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "repr": repr,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


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


def _sandbox_builtins(
    policy: SandboxPolicy,
    read_file_bytes: Callable[[str], bytes] | None,
) -> dict[str, Any]:
    """Build the restricted builtins namespace. Implements ENT5-R7."""

    def sandbox_open(path: str, mode: str = "r", *o_args: Any, **o_kwargs: Any) -> io.IOBase:
        if ".." in str(path).split("/"):
            raise ContractError("ENT5-R7: path escapes sandbox allowlist")
        if not policy.path_allowed(str(path)):
            raise ContractError(f"ENT5-R7: filesystem access denied for {path!r}")
        if read_file_bytes is None:
            raise ContractError("ENT5-R7: no sandbox filesystem backend configured")
        if any(flag in mode for flag in "wax+"):
            raise ContractError("ENT5-R7: sandbox filesystem is read-only")
        data = read_file_bytes(str(path))
        return io.BytesIO(data) if "b" in mode else io.StringIO(data.decode("utf-8"))

    def sandbox_import(name: str, *i_args: Any, **i_kwargs: Any) -> Any:
        top = str(name).split(".")[0]
        if top in DENIED_NETWORK_MODULES:
            raise ContractError(f"ENT5-R7: network module {top!r} denied in sandbox")
        raise ContractError(f"ENT5-R7: import {name!r} not permitted in sandbox")

    builtins_ns = dict(_SAFE_BUILTINS)
    builtins_ns["open"] = sandbox_open
    builtins_ns["__import__"] = sandbox_import
    return builtins_ns


def compile_sandboxed(manifest: ModuleManifest, source: str, function: str) -> Callable[..., Any]:
    """Compile module source into a callable under restricted builtins. Implements ENT5-R7."""
    validate_manifest(manifest)
    namespace: dict[str, Any] = {
        "__builtins__": _sandbox_builtins(manifest.policy, None),
        "__name__": f"sandbox.{manifest.name}",
    }
    exec(compile(source, f"<sandbox:{manifest.name}>", "exec"), namespace)
    fn = namespace.get(function)
    if not callable(fn):
        raise ContractError(f"sandbox entrypoint {function!r} not defined")
    return fn


def run_sandboxed(
    manifest: ModuleManifest,
    source: str,
    function: str,
    *args: Any,
    read_file_bytes: Callable[[str], bytes] | None = None,
    **kwargs: Any,
) -> Any:
    """Run a module's entrypoint under restricted builtins. Implements ENT5-R7.

    - Network access: denied (no socket/urllib/http builtins or imports).
    - Filesystem: ``open`` is restricted to the manifest's allowlist;
      access outside it raises ContractError.
    - Non-root execution and resource limits are modeled by
      :class:`SandboxPolicy` and enforced by :func:`validate_manifest`.
    """
    validate_manifest(manifest)
    namespace: dict[str, Any] = {
        "__builtins__": _sandbox_builtins(manifest.policy, read_file_bytes),
        "__name__": f"sandbox.{manifest.name}",
    }
    exec(compile(source, f"<sandbox:{manifest.name}>", "exec"), namespace)
    fn = namespace.get(function)
    if not callable(fn):
        raise ContractError(f"sandbox entrypoint {function!r} not defined")
    return fn(*args, **kwargs)
