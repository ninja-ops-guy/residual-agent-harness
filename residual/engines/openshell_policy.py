"""Fail-closed policy compilation for the OpenShell R0 adapter.

The output is a RESIDUAL intermediate representation, not a claim that a
particular OpenShell release accepts this exact JSON shape. A live client must
translate the IR to the exact upstream API/CLI schema and then prove the
effective policy before execution can be qualified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..core import ContractError, canonical, digest
from .openshell_contracts import assert_no_inline_secrets

_BROAD_NETWORK = {"*", "0.0.0.0/0", "::/0"}
_BROAD_PATHS = {"*", "/", "/**"}


def _unique_text(values: Sequence[str], name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise ContractError(f"{name} must be a sequence")
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ContractError(f"{name} entries must be non-empty strings")
    if len(result) != len(set(result)):
        raise ContractError(f"{name} contains duplicates")
    return result


@dataclass(frozen=True)
class OpenShellPolicyEnvelope:
    """Least-privilege inputs approved by RESIDUAL before vendor translation."""

    readable_paths: tuple[str, ...] = ()
    writable_paths: tuple[str, ...] = ()
    executable_paths: tuple[str, ...] = ()
    network_destinations: tuple[str, ...] = ()
    provider_refs: tuple[str, ...] = ()
    resource_budget: Mapping[str, int] = field(default_factory=dict)
    inference_route_ref: str | None = None

    def __post_init__(self) -> None:
        readable = _unique_text(self.readable_paths, "readable_paths")
        writable = _unique_text(self.writable_paths, "writable_paths")
        executable = _unique_text(self.executable_paths, "executable_paths")
        network = _unique_text(self.network_destinations, "network_destinations")
        providers = _unique_text(self.provider_refs, "provider_refs")
        for path in readable + writable + executable:
            if path in _BROAD_PATHS:
                raise ContractError("broad filesystem policy is not allowed")
            if not path.startswith("/"):
                raise ContractError("OpenShell filesystem paths must be absolute")
        for destination in network:
            if destination in _BROAD_NETWORK:
                raise ContractError("broad network policy is not allowed")
        if not isinstance(self.resource_budget, Mapping):
            raise ContractError("resource_budget must be a mapping")
        for key, value in self.resource_budget.items():
            if not isinstance(key, str) or not key.strip():
                raise ContractError("resource_budget keys must be non-empty strings")
            if type(value) is not int or value <= 0:
                raise ContractError("resource_budget values must be positive integers")
        if self.inference_route_ref is not None and (
            not isinstance(self.inference_route_ref, str) or not self.inference_route_ref.strip()
        ):
            raise ContractError("inference_route_ref must be non-empty when provided")
        assert_no_inline_secrets(self.payload())

    def payload(self) -> dict[str, Any]:
        return {
            "readable_paths": list(self.readable_paths),
            "writable_paths": list(self.writable_paths),
            "executable_paths": list(self.executable_paths),
            "network_destinations": list(self.network_destinations),
            "provider_refs": list(self.provider_refs),
            "resource_budget": dict(self.resource_budget),
            "inference_route_ref": self.inference_route_ref,
        }


@dataclass(frozen=True)
class CompiledOpenShellPolicy:
    """Canonical RESIDUAL IR to be translated by a live OpenShell client."""

    schema_version: str
    default_action: str
    filesystem: Mapping[str, tuple[str, ...]]
    network: Mapping[str, tuple[str, ...]]
    providers: tuple[str, ...]
    resources: Mapping[str, int]
    inference_route_ref: str | None

    def __post_init__(self) -> None:
        if self.schema_version != "residual.openshell-policy-ir.v1":
            raise ContractError("unsupported OpenShell policy IR schema")
        if self.default_action != "deny":
            raise ContractError("OpenShell R0 policy must default deny")
        canonical(self.payload())
        assert_no_inline_secrets(self.payload())

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "default_action": self.default_action,
            "filesystem": {
                "read": list(self.filesystem.get("read", ())),
                "write": list(self.filesystem.get("write", ())),
                "execute": list(self.filesystem.get("execute", ())),
            },
            "network": {
                "destinations": list(self.network.get("destinations", ())),
            },
            "providers": list(self.providers),
            "resources": dict(self.resources),
            "inference_route_ref": self.inference_route_ref,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True)
class OpenShellPolicyDelta:
    dynamic_changes: tuple[str, ...]
    static_changes: tuple[str, ...]

    @property
    def requires_recreate(self) -> bool:
        return bool(self.static_changes)

    @property
    def has_changes(self) -> bool:
        return bool(self.dynamic_changes or self.static_changes)


def compile_policy(envelope: OpenShellPolicyEnvelope) -> CompiledOpenShellPolicy:
    if not isinstance(envelope, OpenShellPolicyEnvelope):
        raise ContractError("OpenShell policy compilation requires an envelope")
    return CompiledOpenShellPolicy(
        schema_version="residual.openshell-policy-ir.v1",
        default_action="deny",
        filesystem={
            "read": tuple(sorted(envelope.readable_paths)),
            "write": tuple(sorted(envelope.writable_paths)),
            "execute": tuple(sorted(envelope.executable_paths)),
        },
        network={"destinations": tuple(sorted(envelope.network_destinations))},
        providers=tuple(sorted(envelope.provider_refs)),
        resources={key: envelope.resource_budget[key] for key in sorted(envelope.resource_budget)},
        inference_route_ref=envelope.inference_route_ref,
    )


def diff_policy(
    current: CompiledOpenShellPolicy,
    requested: CompiledOpenShellPolicy,
) -> OpenShellPolicyDelta:
    """Classify policy changes conservatively.

    Only network destinations are treated as dynamically mutable in R0. Every
    other difference forces sandbox recreation until a qualified upstream
    capability proves otherwise for an exact OpenShell release/driver tuple.
    """
    if not isinstance(current, CompiledOpenShellPolicy) or not isinstance(
        requested, CompiledOpenShellPolicy
    ):
        raise ContractError("policy diff requires compiled policies")

    dynamic: list[str] = []
    static: list[str] = []

    if current.network != requested.network:
        dynamic.append("network.destinations")
    if current.filesystem != requested.filesystem:
        static.append("filesystem")
    if current.providers != requested.providers:
        static.append("providers")
    if current.resources != requested.resources:
        static.append("resources")
    if current.inference_route_ref != requested.inference_route_ref:
        static.append("inference_route_ref")
    if current.default_action != requested.default_action:
        static.append("default_action")

    return OpenShellPolicyDelta(tuple(dynamic), tuple(static))
