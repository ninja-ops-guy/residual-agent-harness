"""Dependency pinning with hash verification. Implements ENT5-R6.

All dependencies MUST be pinned to exact versions with cryptographic
hashes; no floating version ranges; hashes MUST be verified on
install. Pins use a requirements-style format:

    name==1.2.3 --hash=sha256:<hex>

Range operators (>=, ~=, <, >) and unpinned entries are rejected.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from residual.core import ContractError

_PIN_RE = re.compile(
    r"^(?P<name>[a-zA-Z0-9][a-zA-Z0-9._-]*)==(?P<version>[a-zA-Z0-9][a-zA-Z0-9.!+-]*)"
    r"(?:\s+--hash=sha256:(?P<hash>[0-9a-fA-F]{64}))?\s*$"
)
_FORBIDDEN_OPERATORS = (">=", "<=", "~=", "!=", ">", "<")


@dataclass(frozen=True)
class PinnedDependency:
    """An exact-version, hash-pinned dependency. Implements ENT5-R6."""

    name: str
    version: str
    sha256: str

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ContractError("dependency name required")
        if not isinstance(self.version, str) or not self.version:
            raise ContractError("dependency version required")
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or not re.fullmatch(r"[0-9a-fA-F]{64}", self.sha256)
        ):
            raise ContractError("ENT5-R6: dependency pin requires a sha256 hash")
        object.__setattr__(self, "sha256", self.sha256.lower())

    def verify(self, artifact: bytes) -> bool:
        """Verify artifact bytes against the pinned hash. Implements ENT5-R6."""
        if not isinstance(artifact, bytes):
            raise ContractError("artifact must be bytes")
        return hashlib.sha256(artifact).hexdigest() == self.sha256


def parse_pins(text: str) -> list[PinnedDependency]:
    """Parse a requirements-style pin file. Implements ENT5-R6.

    Every non-comment line MUST be an exact ``==`` pin with a
    ``--hash=sha256:`` entry. Floating ranges and missing hashes are
    rejected per ENT5-R6.
    """
    if not isinstance(text, str):
        raise ContractError("pin file must be text")
    pins: list[PinnedDependency] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for op in _FORBIDDEN_OPERATORS:
            if op in line:
                raise ContractError(
                    f"ENT5-R6: floating version range forbidden on line {lineno}: {line!r}"
                )
        match = _PIN_RE.match(line)
        if not match:
            raise ContractError(f"line {lineno}: not an exact pinned requirement: {line!r}")
        if not match.group("hash"):
            raise ContractError(
                f"ENT5-R6: line {lineno} is missing --hash=sha256: {line!r}"
            )
        dep = PinnedDependency(
            name=match.group("name"),
            version=match.group("version"),
            sha256=match.group("hash"),
        )
        if any(p.name == dep.name for p in pins):
            raise ContractError(f"duplicate pin for {dep.name!r}")
        pins.append(dep)
    return pins


def verify_pin(pin: PinnedDependency, artifact: bytes) -> None:
    """Verify one pinned dependency's artifact hash on install. Implements ENT5-R6."""
    if not isinstance(pin, PinnedDependency):
        raise ContractError("pin must be a PinnedDependency")
    if not pin.verify(artifact):
        raise ContractError(
            f"ENT5-R6: hash mismatch for {pin.name}=={pin.version}; install aborted"
        )


def verify_all(pins: list[PinnedDependency], artifacts: dict[str, bytes]) -> None:
    """Verify every pinned dependency against its artifact. Implements ENT5-R6.

    ``artifacts`` maps dependency name to artifact bytes. Every pin
    MUST have a corresponding artifact; any mismatch aborts install.
    """
    names = {p.name for p in pins}
    extra = set(artifacts) - names
    if extra:
        raise ContractError(f"artifacts without pins: {sorted(extra)}")
    for pin in pins:
        if pin.name not in artifacts:
            raise ContractError(f"missing artifact for pinned dependency {pin.name!r}")
        verify_pin(pin, artifacts[pin.name])
