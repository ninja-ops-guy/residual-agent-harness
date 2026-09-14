"""Host-selected, reverified memory at the context-assembly boundary."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core import ContractError, canonical, strict_json
from ..engines.protocol import ContextAssembly
from ..receipts import hash_id
from .store import EpistemicMemoryStore


@dataclass(frozen=True)
class MemoryRequest:
    name: str
    description: str
    verifier_revision: str
    verify: Callable

    def __post_init__(self):
        from ..core import identifier
        identifier(self.name)
        hash_id(self.verifier_revision)
        if not self.description.strip() or not callable(self.verify):
            raise ContractError("memory requests require a description and a live host verifier")


class MemoryContextAssembler:
    """Explicit requests only: no model-nominated searches or implicit data export.

    The verifier callback must bind the active goal, inputs, parents and evidence.
    Successful integrity checks alone never authorize reuse. The caller decides
    the disclosure scope of the resulting context before choosing an engine.
    """
    def __init__(self, store: EpistemicMemoryStore, requests: tuple[MemoryRequest, ...],
                 *, max_bytes: int = 64_000):
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ContractError("context budget must be a positive byte count")
        if len({r.name for r in requests}) != len(requests):
            raise ContractError("duplicate memory request")
        self.store, self.requests, self.max_bytes = store, tuple(requests), max_bytes

    def assemble(self, base: dict | None = None) -> ContextAssembly:
        values = strict_json(canonical(base or {}))
        if "memory" in values:
            raise ContractError("memory must not shadow a host context value")
        memory = {}
        for request in self.requests:
            entry = self.store.retrieve_verified(request.description,
                verifier_revision=request.verifier_revision, verify=request.verify)
            if entry is None:
                continue
            item = {"value": strict_json(canonical(entry.artifact_payload["value"])),
                    "receipt_hash": entry.receipt_hash,
                    "verifier_revision": entry.verifier_revision}
            trial = {**values, "memory": {**memory, request.name: item}}
            if len(canonical(trial).encode()) <= self.max_bytes:
                memory[request.name] = item
        result = {**values, "memory": memory}
        if len(canonical(result).encode()) > self.max_bytes:
            raise ContractError("base context exceeds the assembly byte budget")
        return ContextAssembly(result)
