"""Deterministic routing across evidence-qualified execution substrates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..core import ContractError
from .protocol import ExecutionSubstrate, SubstrateHealth
from .qualification import (
    SubstrateQualificationRecord,
    SubstrateQualificationRegistry,
    SubstrateQualificationTuple,
)


class SubstrateRoutingError(LookupError):
    """No exact qualified substrate can satisfy the requested execution contract."""


@dataclass(frozen=True)
class RegisteredSubstrate:
    substrate: ExecutionSubstrate
    qualification_tuple: SubstrateQualificationTuple
    qualification_record_digest: str

    @property
    def key(self) -> str:
        return (
            f"{self.substrate.name}@{self.substrate.version}:"
            f"{self.qualification_tuple.driver}:"
            f"{self.qualification_tuple.platform_class}:"
            f"{self.qualification_tuple.tuple_digest[:12]}"
        )


class QualifiedSubstrateRouter:
    """Routes only across exact tuples with pinned PASS qualification records."""

    _LOCALITY_ORDER = {"local": 0, "cluster": 1, "cloud": 2}

    def __init__(self, registry: SubstrateQualificationRegistry):
        if not isinstance(registry, SubstrateQualificationRegistry):
            raise ContractError("router requires SubstrateQualificationRegistry")
        self._registry = registry
        self._entries: dict[str, RegisteredSubstrate] = {}

    def register(
        self,
        substrate: ExecutionSubstrate,
        qualification_tuple: SubstrateQualificationTuple,
        *,
        record_digest: str,
    ) -> None:
        if not isinstance(substrate, ExecutionSubstrate):
            raise ContractError("registered object does not implement ExecutionSubstrate")
        record = self._registry.get(qualification_tuple, record_digest=record_digest)
        if record is None:
            raise SubstrateRoutingError("pinned qualification record does not exist")
        if record.overall != "PASS":
            raise SubstrateRoutingError(
                f"cannot register non-PASS qualification: {record.overall}"
            )
        identity = substrate.substrate_identity()
        expected = qualification_tuple
        mismatches = []
        if identity.name != expected.substrate_name:
            mismatches.append("substrate_name")
        if identity.version != expected.substrate_version:
            mismatches.append("substrate_version")
        if identity.source_identity != expected.substrate_source_identity:
            mismatches.append("substrate_source_identity")
        if identity.driver != expected.driver:
            mismatches.append("driver")
        if identity.platform_class != expected.platform_class:
            mismatches.append("platform_class")
        if identity.environment_digest != expected.environment_digest:
            mismatches.append("environment_digest")
        if mismatches:
            raise SubstrateRoutingError(
                "runtime identity does not match qualified tuple: " + ",".join(mismatches)
            )
        entry = RegisteredSubstrate(substrate, qualification_tuple, record_digest)
        if entry.key in self._entries:
            raise SubstrateRoutingError(f"duplicate substrate registration: {entry.key}")
        self._entries[entry.key] = entry

    def route(
        self,
        required_capabilities: Iterable[str],
        *,
        driver: str | None = None,
        platform_class: str | None = None,
        agent_profile: str | None = None,
    ) -> RegisteredSubstrate:
        capabilities = tuple(sorted(set(required_capabilities)))
        if not capabilities or any(
            not isinstance(capability, str) or not capability.strip()
            for capability in capabilities
        ):
            raise SubstrateRoutingError("required capabilities must be non-empty strings")

        eligible: list[tuple[tuple, RegisteredSubstrate]] = []
        diagnostics: list[str] = []
        for entry in self._entries.values():
            qtuple = entry.qualification_tuple
            if driver is not None and qtuple.driver != driver:
                continue
            if platform_class is not None and qtuple.platform_class != platform_class:
                continue
            if agent_profile is not None and qtuple.agent_profile != agent_profile:
                continue

            health = entry.substrate.substrate_health()
            if health != SubstrateHealth.HEALTHY:
                diagnostics.append(f"{entry.key}:health={health.value}")
                continue

            record = self._registry.get(
                qtuple,
                record_digest=entry.qualification_record_digest,
            )
            if record is None or record.overall != "PASS":
                diagnostics.append(f"{entry.key}:qualification_unavailable")
                continue
            missing = sorted(set(capabilities) - record.qualified_capabilities)
            if missing:
                diagnostics.append(f"{entry.key}:missing={','.join(missing)}")
                continue

            locality_rank = self._LOCALITY_ORDER.get(entry.substrate.locality, 99)
            sort_key = (
                locality_rank,
                entry.substrate.name,
                entry.substrate.version,
                qtuple.driver,
                qtuple.platform_class,
                qtuple.tuple_digest,
                entry.qualification_record_digest,
            )
            eligible.append((sort_key, entry))

        if not eligible:
            suffix = "; ".join(sorted(diagnostics))
            raise SubstrateRoutingError(
                "no exact qualified substrate satisfies capabilities"
                + (f": {suffix}" if suffix else "")
            )
        eligible.sort(key=lambda item: item[0])
        return eligible[0][1]

    def snapshot(self) -> tuple[dict, ...]:
        rows = []
        for key in sorted(self._entries):
            entry = self._entries[key]
            record = self._registry.get(
                entry.qualification_tuple,
                record_digest=entry.qualification_record_digest,
            )
            rows.append({
                "key": key,
                "health": entry.substrate.substrate_health().value,
                "tuple_digest": entry.qualification_tuple.tuple_digest,
                "record_digest": entry.qualification_record_digest,
                "overall": None if record is None else record.overall,
                "capabilities": [] if record is None else sorted(record.qualified_capabilities),
                "limitations": [] if record is None else sorted(record.limitations),
            })
        return tuple(rows)
