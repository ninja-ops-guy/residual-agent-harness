"""StationLM model registry: qualification state machine + manifests.

Registry authority stays in RESIDUAL. A model may only serve advisory traffic
from ``qualified`` state, and reaching ``qualified`` requires a qualification
receipt reference. States: candidate -> staged -> qualified; any non-terminal
state -> rejected (terminal). Rollback demotes qualified -> rejected.
"""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from residual.core import ContractError, canonical, identifier

_STATES = ("candidate", "staged", "qualified", "rejected")
_TRANSITIONS = {
    "candidate": {"staged", "rejected"},
    "staged": {"qualified", "rejected", "candidate"},
    "qualified": {"rejected"},
    "rejected": set(),  # terminal
}
_HASH = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{7,40}")
MODEL_CARD_FIELDS = {"name", "version", "intended_use", "limitations"}


@dataclass(frozen=True)
class ModelManifest:
    """Provenance manifest for one StationLM candidate."""

    model_id: str
    model_hash: str
    tokenizer_hash: str
    dataset_manifest_hash: str
    training_config: dict[str, Any]
    code_commit: str
    seed: int
    qualification_receipt: Optional[str] = None
    model_card: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        identifier(self.model_id)
        for label, value in (("model_hash", self.model_hash),
                             ("tokenizer_hash", self.tokenizer_hash),
                             ("dataset_manifest_hash", self.dataset_manifest_hash)):
            if not isinstance(value, str) or not _HASH.fullmatch(value):
                raise ContractError(f"{label} must be a lowercase SHA-256 digest")
        if not isinstance(self.code_commit, str) or not _COMMIT.fullmatch(self.code_commit):
            raise ContractError("code_commit must be a lowercase git commit hex")
        if type(self.seed) is not int or self.seed < 0:
            raise ContractError("seed must be a nonnegative integer")
        if self.qualification_receipt is not None and (
                not isinstance(self.qualification_receipt, str)
                or not _HASH.fullmatch(self.qualification_receipt)):
            raise ContractError("qualification_receipt must be a SHA-256 digest")
        if not isinstance(self.training_config, dict) or not isinstance(self.model_card, dict):
            raise ContractError("training_config/model_card must be objects")
        canonical(self.training_config)
        canonical(self.model_card)
        missing = MODEL_CARD_FIELDS - set(self.model_card)
        if missing:
            raise ContractError(f"model_card missing fields: {sorted(missing)}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelManifest":
        if not isinstance(data, dict) or set(data) - {
                "model_id", "model_hash", "tokenizer_hash", "dataset_manifest_hash",
                "training_config", "code_commit", "seed", "qualification_receipt",
                "model_card"}:
            raise ContractError("unknown manifest keys")
        return cls(**data)


@dataclass(frozen=True)
class RegistryEntry:
    manifest: ModelManifest
    state: str
    history: tuple[dict, ...] = ()


class ModelRegistry:
    """In-memory registry with an explicit, auditable state machine."""

    def __init__(self, clock=None):
        self._entries: dict[str, RegistryEntry] = {}
        self._clock = clock or time.time

    def _log(self, model_id: str, source: str, target: str, reason: str,
             receipt: Optional[str]) -> dict:
        return {"model_id": model_id, "from": source, "to": target,
                "reason": reason, "qualification_receipt": receipt,
                "timestamp": self._clock()}

    def register(self, manifest: ModelManifest) -> RegistryEntry:
        if not isinstance(manifest, ModelManifest):
            raise ContractError("register requires a ModelManifest")
        existing = self._entries.get(manifest.model_id)
        if existing is not None:
            if existing.manifest != manifest:
                raise ContractError("model_id re-registered with a different manifest")
            return existing
        entry = RegistryEntry(manifest, "candidate",
                              (self._log(manifest.model_id, "none", "candidate",
                                         "registered", None),))
        self._entries[manifest.model_id] = entry
        return entry

    def transition(self, model_id: str, target: str, *, reason: str = "",
                   qualification_receipt: Optional[str] = None) -> RegistryEntry:
        entry = self._entries.get(model_id)
        if entry is None:
            raise ContractError("unknown model")
        if target not in _STATES:
            raise ContractError("unknown registry state")
        if target not in _TRANSITIONS[entry.state]:
            raise ContractError(f"illegal transition {entry.state}->{target}")
        receipt = qualification_receipt or entry.manifest.qualification_receipt
        if target == "qualified":
            # Qualification is receipt-gated; self-attestation is not enough.
            if not isinstance(receipt, str) or not _HASH.fullmatch(receipt):
                raise ContractError("qualification requires a qualification receipt")
        if target == "rejected" and not reason:
            raise ContractError("rejection requires a reason")
        entry = RegistryEntry(entry.manifest, target,
                              entry.history + (self._log(model_id, entry.state, target,
                                                         reason, receipt),))
        self._entries[model_id] = entry
        return entry

    def get(self, model_id: str) -> RegistryEntry:
        entry = self._entries.get(model_id)
        if entry is None:
            raise ContractError("unknown model")
        return entry

    def state_of(self, model_id: str) -> str:
        return self.get(model_id).state

    def qualified_manifest(self, model_id: str) -> ModelManifest:
        """Only a qualified model may serve advisory traffic."""
        entry = self.get(model_id)
        if entry.state != "qualified":
            raise ContractError(f"model {model_id} is not qualified")
        return entry.manifest

    def rollback(self, model_id: str, reason: str) -> RegistryEntry:
        """Qualified -> rejected. Latching; re-entry requires a new candidate."""
        return self.transition(model_id, "rejected", reason=reason)

    def names(self) -> list[str]:
        return sorted(self._entries)
