"""Track E: deterministic resume after HITL escalation.

Requirement IDs (RFC 2119):
- E-R9: Suspending a run MUST persist a content-addressed checkpoint whose
  state hash is recorded in the Suspension token.
- E-R10: Resume MUST fail closed unless the referenced HITL challenge is in
  status APPROVED. Pending, denied, expired, or forged challenges MUST NOT
  resume a run.
- E-R11: Resume MUST reconstruct run state deterministically: the state hash
  after resume MUST equal the state hash recorded at suspension; any
  divergence (tampered or missing checkpoint) MUST raise ContractError.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from observation_layer.core import freeze

from ..core import ContractError, digest, identifier, positive_int
from ..goalspec import GoalSpec
from ..hitl import HITLEscalationGateway, HITLStatus
from .checkpoints import Checkpoint, CheckpointStore


@dataclass(frozen=True)
class RunState:
    """Minimal deterministic run state carried across a HITL suspension."""

    run_id: str
    step: int
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        identifier(self.run_id)
        positive_int(self.step, "step", allow_zero=True)
        if not isinstance(self.data, dict):
            raise ContractError("run state data must be a dict")
        try:
            object.__setattr__(self, "data", freeze(self.data))
        except Exception:
            raise ContractError("run state data must be canonicalizable")

    @property
    def state_hash(self) -> str:
        """Deterministic: pure function of (run_id, step, data)."""
        return digest({"run_id": self.run_id, "step": self.step, "data": self.data})


@dataclass(frozen=True)
class Suspension:
    """Token binding a run's suspension to its checkpoint and HITL challenge."""

    run_id: str
    checkpoint_hash: str
    challenge_id: str
    state_hash: str        # recorded at suspension; resume MUST reproduce it


class DeterministicResumer:
    """E-R9..E-R11: suspend a run for HITL, resume it bit-identically."""

    def __init__(self, hitl_gateway: HITLEscalationGateway,
                 checkpoint_store: CheckpointStore):
        if not isinstance(hitl_gateway, HITLEscalationGateway):
            raise ContractError("resume requires a HITL escalation gateway")
        if not isinstance(checkpoint_store, CheckpointStore):
            raise ContractError("resume requires a checkpoint store")
        self._hitl = hitl_gateway
        self._checkpoints = checkpoint_store

    def suspend(self, state: RunState, *, task_id: str,
                proposed_action: dict[str, Any], reason: str,
                goal_spec: GoalSpec) -> Suspension:
        """E-R9: checkpoint the state and open a HITL challenge."""
        if not isinstance(state, RunState):
            raise ContractError("suspend requires a RunState")
        checkpoint = self._checkpoints.save(state.run_id, state.step, state.data)
        challenge = self._hitl.generate_challenge(task_id, proposed_action, reason, goal_spec)
        return Suspension(run_id=state.run_id,
                          checkpoint_hash=checkpoint.checkpoint_hash,
                          challenge_id=challenge.challenge_id,
                          state_hash=state.state_hash)

    def challenge_status(self, suspension: Suspension) -> Optional[HITLStatus]:
        record = self._hitl.get_challenge(suspension.challenge_id)
        if record is None:
            return None
        try:
            return HITLStatus(record["status"])
        except (ValueError, KeyError):
            return None

    def resume(self, suspension: Suspension) -> RunState:
        """E-R10/E-R11: approved-only, hash-verified deterministic resume."""
        if not isinstance(suspension, Suspension):
            raise ContractError("resume requires a Suspension token")
        if self.challenge_status(suspension) is not HITLStatus.APPROVED:
            raise ContractError("resume requires an approved HITL challenge")
        checkpoint: Optional[Checkpoint] = self._checkpoints.load(suspension.checkpoint_hash)
        if checkpoint is None or checkpoint.run_id != suspension.run_id:
            raise ContractError("checkpoint missing or does not verify")
        resumed = RunState(run_id=checkpoint.run_id, step=checkpoint.step,
                           data=checkpoint.state)
        if resumed.state_hash != suspension.state_hash:
            raise ContractError("resumed state diverges from suspended state hash")
        return resumed
