"""Track E: auto-indexing of successful runs into the epistemic memory layer.

Requirement IDs (RFC 2119):
- E-R1: Only runs with outcome SUCCESS MUST be indexed; escalated, aborted,
  or amended runs MUST NOT enter memory.
- E-R2: An indexed artifact MUST be bound to a passing host receipt whose
  value_hash equals digest(value); a mismatched receipt MUST be rejected.
- E-R3: Indexing MUST happen at run close (via the lifecycle bus) or through
  the explicit ``auto_index_run`` entry point — never mid-run.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from ..core import ContractError, digest
from ..loop import RunOutcome
from ..memory import EpistemicMemoryStore, MemoryEntry
from ..receipts import StationReceipt


def auto_index_run(store: EpistemicMemoryStore, description: str,
                   receipt: StationReceipt, value: Any,
                   outcome: RunOutcome) -> Optional[MemoryEntry]:
    """E-R1/E-R2: index one successful, receipt-bound run result.

    Returns the MemoryEntry on success, None when the run did not succeed.
    Raises ContractError when a successful run's receipt does not bind.
    """
    if not isinstance(store, EpistemicMemoryStore):
        raise ContractError("auto-indexing requires an EpistemicMemoryStore")
    try:
        outcome = RunOutcome(outcome)
    except (ValueError, TypeError):
        raise ContractError("unknown run outcome") from None
    if outcome is not RunOutcome.SUCCESS:
        return None
    if (not isinstance(receipt, StationReceipt)
            or receipt.verdict.value != "pass"
            or receipt.value_hash != digest(value)):
        raise ContractError("memory requires a bound passing host receipt")
    return store.index(description, receipt.receipt_hash,
                       {"receipt": receipt.to_dict(), "value": value},
                       receipt.verifier_revision)


def bind_indexing(bus, store: EpistemicMemoryStore,
                  receipt_resolver: Callable, *, publish=None):
    """E-R3: lifecycle binding — auto-index at run close.

    Delegates to ``residual.lifecycle.bind_memory``; the bus emits run_closed
    and the host-owned resolver yields (description, receipt, value) tuples.
    """
    from ..lifecycle import bind_memory
    return bind_memory(bus, store, receipt_resolver, publish=publish)
