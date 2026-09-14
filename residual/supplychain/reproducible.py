"""Reproducible build verification. Implements ENT5-R8.

The build process MUST be reproducible: given the same source code
and build environment, the build MUST produce bit-identical output,
and reproducibility MUST be verified in CI for every release.
:func:`verify_reproducible` rebuilds from a signed
:class:`~residual.supplychain.signing.BuildManifest` and compares the
rebuilt output hashes against the manifest.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from residual.core import ContractError
from residual.supplychain.signing import BuildManifest


@dataclass(frozen=True)
class ReproducibilityReport:
    """Result of a CI reproducibility check. Implements ENT5-R8."""

    manifest_sha256: str
    reproducible: bool
    mismatched_outputs: tuple[str, ...]
    verified_outputs: tuple[str, ...]

    def __post_init__(self):
        if type(self.reproducible) is not bool:
            raise ContractError("reproducible flag must be bool")
        if self.reproducible and self.mismatched_outputs:
            raise ContractError("reproducible report cannot list mismatches")

    def to_dict(self) -> dict:
        """Published verification result. Implements ENT5-R8."""
        return {
            "manifest_sha256": self.manifest_sha256,
            "reproducible": self.reproducible,
            "mismatched_outputs": list(self.mismatched_outputs),
            "verified_outputs": list(self.verified_outputs),
        }


def verify_reproducible(
    manifest: BuildManifest,
    rebuild: Callable[[BuildManifest], dict[str, str]],
    environment: dict[str, str] | None = None,
) -> ReproducibilityReport:
    """Rebuild from a manifest and compare output hashes. Implements ENT5-R8.

    ``rebuild`` maps a manifest to ``{path: sha256}`` for the rebuilt
    outputs. ``environment`` optionally pins the build environment;
    if provided it MUST equal the manifest's recorded environment,
    since reproducibility is defined given the same build environment.
    """
    if not isinstance(manifest, BuildManifest):
        raise ContractError("manifest must be a BuildManifest")
    if not callable(rebuild):
        raise ContractError("rebuild must be callable")
    if environment is not None and dict(environment) != dict(manifest.environment):
        raise ContractError(
            "ENT5-R8: build environment differs from manifest; reproducibility undefined"
        )
    rebuilt = rebuild(manifest)
    if not isinstance(rebuilt, dict):
        raise ContractError("rebuild must return a dict of path -> sha256")
    mismatched: list[str] = []
    verified: list[str] = []
    for path in sorted(manifest.outputs):
        expected = manifest.outputs[path]
        actual = rebuilt.get(path)
        if actual is None or actual != expected:
            mismatched.append(path)
        else:
            verified.append(path)
    extra = sorted(set(rebuilt) - set(manifest.outputs))
    mismatched.extend(extra)
    return ReproducibilityReport(
        manifest_sha256=manifest.sha256,
        reproducible=not mismatched,
        mismatched_outputs=tuple(mismatched),
        verified_outputs=tuple(verified),
    )
