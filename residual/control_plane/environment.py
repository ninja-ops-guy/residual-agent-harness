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
        """Return (accepted, actual_fingerprint, reason); all errors fail closed."""
        record=self.expected(worker_id)
        if record is None: return False, None, "worker_not_registered"
        try: actual=attestor(worker_id)
        except Exception as exc: return False, None, f"attestor_error:{type(exc).__name__}"
        try: actual_fp=digest(actual)
        except Exception as exc: return False, None, f"attestation_uncanonicalizable:{type(exc).__name__}"
        if actual_fp != record.fingerprint: return False, actual_fp, "fingerprint_mismatch"
        return True, actual_fp, "attested"
