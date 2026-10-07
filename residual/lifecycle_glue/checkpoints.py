"""Track E: replay checkpoints — deterministic, content-addressed run state.

Requirement IDs (RFC 2119):
- E-R6: A checkpoint MUST be content-addressed: identical (run_id, step,
  state) tuples MUST produce identical checkpoint hashes. Wall-clock time
  MUST NOT enter the hash.
- E-R7: Loading a checkpoint MUST re-verify the content hash; tampered
  checkpoints MUST be rejected.
- E-R8: Checkpoint state MUST be canonicalizable JSON; non-serializable
  state MUST be rejected at save time.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from observation_layer.core import freeze

from ..core import ContractError, canonical, digest, identifier, positive_int, strict_json
from ..receipts import hash_id

SCHEMA = "residual.lifecycle.checkpoint.v1"


@dataclass(frozen=True)
class Checkpoint:
    """E-R6: immutable, content-addressed snapshot of run state."""

    checkpoint_hash: str
    run_id: str
    step: int
    state: dict[str, Any]

    @property
    def state_hash(self) -> str:
        return digest(self.state)


class CheckpointStore:
    """Content-addressed checkpoint store with per-run ordering."""

    def __init__(self, checkpoint_dir: str):
        if not checkpoint_dir:
            raise ContractError("checkpoint directory is required")
        self._dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

    @staticmethod
    def _content(run_id: str, step: int, state: dict[str, Any]) -> dict:
        return {"schema_version": SCHEMA, "run_id": run_id, "step": step, "state": state}

    def save(self, run_id: str, step: int, state: dict[str, Any]) -> Checkpoint:
        """E-R6/E-R8: save a deterministic, canonicalizable snapshot."""
        identifier(run_id)
        positive_int(step, "step", allow_zero=True)
        if not isinstance(state, dict):
            raise ContractError("checkpoint state must be a dict")
        try:
            frozen = freeze(state)
            content = self._content(run_id, step, frozen)
            checkpoint_hash = digest(content)
        except Exception:
            raise ContractError("checkpoint state must be canonicalizable") from None
        path = os.path.join(self._dir, f"{checkpoint_hash}.json")
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(content, f, indent=2, sort_keys=True)
        return Checkpoint(checkpoint_hash=checkpoint_hash, run_id=run_id,
                          step=step, state=frozen)

    def load(self, checkpoint_hash: str) -> Optional[Checkpoint]:
        """E-R7: load and re-verify. Tampered content returns None."""
        hash_id(checkpoint_hash)
        path = os.path.join(self._dir, f"{checkpoint_hash}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = strict_json(f.read())
            if (data.get("schema_version") != SCHEMA
                    or digest(data) != checkpoint_hash):
                return None
            return Checkpoint(checkpoint_hash=checkpoint_hash,
                              run_id=data["run_id"], step=data["step"],
                              state=freeze(data["state"]))
        except (ValueError, KeyError, TypeError, OSError):
            return None

    def history(self, run_id: str) -> tuple[Checkpoint, ...]:
        """All checkpoints for a run, ordered by step (replay order)."""
        identifier(run_id)
        found = []
        for name in sorted(os.listdir(self._dir)):
            if not name.endswith(".json"):
                continue
            cp = self.load(name[:-5])
            if cp is not None and cp.run_id == run_id:
                found.append(cp)
        return tuple(sorted(found, key=lambda c: (c.step, c.checkpoint_hash)))
