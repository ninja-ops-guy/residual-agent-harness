"""RUN-R4: engine name/version/provider metadata in receipts and records."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core import ContractError, digest
from ..engines.protocol import EngineResult, ExecutionEngine, TaskSpec

RECORD_SCHEMA = "residual.runtime.execution_record.v1"


def engine_identity(engine: ExecutionEngine) -> dict[str, str]:
    """Normalized name/version/provider identity for an engine."""
    name = getattr(engine, "name", "")
    version = getattr(engine, "version", "")
    if not isinstance(name, str) or not name.strip():
        raise ContractError("engine name is required for runtime records")
    if not isinstance(version, str) or not version.strip():
        raise ContractError("engine version is required for runtime records")
    # Provider is derived from the adapter surface, never from credentials.
    provider = str(engine.raw_provider) if hasattr(engine, "raw_provider") else ""
    if not provider:
        # "provider:<provider>:<model>" names expose the provider segment.
        provider = name.split(":")[1] if name.startswith("provider:") else name
    return {
        "engine_name": name,
        "engine_version": version,
        "engine_provider": provider,
        "engine_locality": str(getattr(engine, "locality", "unknown")),
        "engine_capability_class": str(getattr(engine, "capability_class", "unknown")),
    }


@dataclass(frozen=True)
class EngineExecutionRecord:
    """Evaluation record binding engine identity to an execution outcome.

    ``station_receipt_payload`` carries engine_name/engine_version (receipt v2
    fields); the record itself additionally binds the provider. The record hash
    covers all identity fields so metadata cannot be stripped silently.
    """

    task_id: str
    engine_name: str
    engine_version: str
    engine_provider: str
    engine_locality: str
    engine_capability_class: str
    capability: str
    candidate_digest: str
    station_receipt_payload: Mapping[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": RECORD_SCHEMA,
            "task_id": self.task_id,
            "capability": self.capability,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "engine_provider": self.engine_provider,
            "engine_locality": self.engine_locality,
            "engine_capability_class": self.engine_capability_class,
            "candidate_digest": self.candidate_digest,
            "station_receipt": dict(self.station_receipt_payload),
        }

    @property
    def record_hash(self) -> str:
        return digest(self.payload())


def build_execution_record(engine: ExecutionEngine, task: TaskSpec,
                           result: EngineResult) -> EngineExecutionRecord:
    """Build a receipt-bearing evaluation record for one engine execution."""
    ident = engine_identity(engine)
    candidate_digest = digest({"candidate": result.candidate})
    # Receipt payload mirrors the v2 receipt provenance fields.
    receipt_payload = {
        "engine_name": ident["engine_name"],
        "engine_version": ident["engine_version"],
        "engine_provider": ident["engine_provider"],
        "task_id": task.task_id,
        "candidate_digest": candidate_digest,
    }
    receipt_payload["receipt_digest"] = digest(receipt_payload)
    return EngineExecutionRecord(
        task_id=task.task_id,
        engine_name=ident["engine_name"],
        engine_version=ident["engine_version"],
        engine_provider=ident["engine_provider"],
        engine_locality=ident["engine_locality"],
        engine_capability_class=ident["engine_capability_class"],
        capability=task.capability,
        candidate_digest=candidate_digest,
        station_receipt_payload=receipt_payload,
    )
