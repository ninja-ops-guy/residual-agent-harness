"""Spike-only A2A↔RESIDUAL identity binding. Carries no acceptance authority."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, json
from typing import Optional, Tuple

@dataclass(frozen=True)
class BindingRecord:
    task_id: str
    context_id: Optional[str]
    message_id: Optional[str]
    run_id: str
    obligation_id: str
    snapshot_refs: Tuple[str, ...] = ()

    def canonical(self) -> bytes:
        return json.dumps({
            "a2a":{"context_id":self.context_id,"message_id":self.message_id,"task_id":self.task_id},
            "residual":{"obligation_id":self.obligation_id,"run_id":self.run_id},
            "snapshot_refs":list(self.snapshot_refs),
        }, sort_keys=True, separators=(",",":")).encode()

    @property
    def binding_id(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical()).hexdigest()
