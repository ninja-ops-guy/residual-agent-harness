"""Persistent content-addressed ledger for execution-substrate qualification."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..core import ContractError, canonical, digest, strict_json
from .qualification import (
    SubstrateQualificationRecord,
    SubstrateQualificationRegistry,
    qualification_record_from_payload,
)


@dataclass(frozen=True)
class SubstrateQualificationLedger:
    records: tuple[SubstrateQualificationRecord, ...]
    schema_version: str = "residual.substrate-qualification-ledger.v1"

    def __post_init__(self) -> None:
        if self.schema_version != "residual.substrate-qualification-ledger.v1":
            raise ContractError("unsupported substrate qualification ledger schema")
        if any(not isinstance(record, SubstrateQualificationRecord) for record in self.records):
            raise ContractError("ledger contains invalid qualification record")
        digests = [record.record_digest for record in self.records]
        if len(digests) != len(set(digests)):
            raise ContractError("ledger contains duplicate qualification record")

    def payload(self) -> dict[str, Any]:
        rows = sorted(
            (
                {
                    "record_digest": record.record_digest,
                    "record": record.payload(),
                }
                for record in self.records
            ),
            key=lambda row: row["record_digest"],
        )
        return {
            "schema_version": self.schema_version,
            "records": rows,
        }

    @property
    def ledger_digest(self) -> str:
        return digest(self.payload())

    def registry(self) -> SubstrateQualificationRegistry:
        registry = SubstrateQualificationRegistry()
        for record in self.records:
            registry.add(record)
        return registry

    def write(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(canonical(self.payload()) + "\n", encoding="utf-8")

    @classmethod
    def from_registry(
        cls,
        registry: SubstrateQualificationRegistry,
    ) -> "SubstrateQualificationLedger":
        if not isinstance(registry, SubstrateQualificationRegistry):
            raise ContractError("ledger requires SubstrateQualificationRegistry")
        return cls(registry.records())

    @classmethod
    def load(cls, path: str | Path) -> "SubstrateQualificationLedger":
        payload = strict_json(Path(path).read_text(encoding="utf-8"))
        return cls.from_payload(payload)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
    ) -> "SubstrateQualificationLedger":
        if set(payload) != {"schema_version", "records"}:
            raise ContractError("qualification ledger keys do not match schema")
        if payload["schema_version"] != "residual.substrate-qualification-ledger.v1":
            raise ContractError("unsupported substrate qualification ledger schema")
        records = []
        for row in payload["records"]:
            if set(row) != {"record_digest", "record"}:
                raise ContractError("qualification ledger row keys do not match schema")
            record = qualification_record_from_payload(row["record"])
            if row["record_digest"] != record.record_digest:
                raise ContractError("qualification record digest mismatch")
            records.append(record)
        return cls(tuple(records), schema_version=payload["schema_version"])
