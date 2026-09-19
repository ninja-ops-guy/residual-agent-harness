"""F0 canaries for SPIKE-A2A-000.

These deliberately use a tiny spike model before SDK wiring. The property under
test is the authority boundary: remote COMPLETED or an artifact is never PASS.
"""
from dataclasses import dataclass

@dataclass
class Candidate:
    value: int
    terminal: bool = False

def authoritative_verify(candidate: Candidate, expected: int) -> bool:
    return candidate.terminal and candidate.value == expected

def accepted_receipt(candidate: Candidate, expected: int):
    return {"accepted": True} if authoritative_verify(candidate, expected) else None

def test_completed_with_incorrect_artifact_fails():
    remote_completed = Candidate(value=41, terminal=True)
    assert authoritative_verify(remote_completed, expected=42) is False
    assert accepted_receipt(remote_completed, expected=42) is None

def test_connection_death_no_silent_promotion():
    artifact_before_disconnect = Candidate(value=42, terminal=False)
    assert accepted_receipt(artifact_before_disconnect, expected=42) is None
    # Reconciliation may recover bytes, but cannot invent terminal/verification state.
    recovered = Candidate(value=artifact_before_disconnect.value, terminal=False)
    assert accepted_receipt(recovered, expected=42) is None
