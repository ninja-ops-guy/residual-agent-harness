"""Control-plane-owned expected environment registry and attestation checks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from ..core import digest

@dataclass(frozen=True)
class EnvironmentRecord:
    worker_id: str; expected: Mapping[str,Any]; registry_revision: str
    @property
    def fingerprint(self): return digest(self.expected)

class EnvironmentRegistry:
    def __init__(self): self._records={}
    def register(self, record: EnvironmentRecord): self._records[record.worker_id]=record
    def expected(self, worker_id): return self._records.get(worker_id)
    def attest(self, worker_id: str, attestor: Callable[[str],Mapping[str,Any]]):
        record=self.expected(worker_id)
        if record is None: return False, None
        try: actual=attestor(worker_id)
        except Exception: return False, None
        actual_fp=digest(actual)
        return actual_fp==record.fingerprint, actual_fp
