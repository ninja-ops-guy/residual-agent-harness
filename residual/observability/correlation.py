"""Trace <-> receipt-ID correlation (Track N, N-R4).

Additive module. A ``CorrelationContext`` carries W3C-traceparent-shaped
trace/span IDs plus the receipt hash of the current task, so every log line,
metric label set, and span emitted during a run can be joined back to the
receipt that proves the run. Provides:

- ``new_trace_id`` / ``new_span_id``: random hex IDs in W3C format.
- ``CorrelationContext``: immutable carrier; ``traceparent`` header value;
  ``bind_receipt`` returns a new context with the receipt attached.
- ``TraceReceiptIndex``: bidirectional lookup trace_id <-> receipt_hash with
  span listing; lookups MUST be exact and deterministic.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field, replace

from ..core import ContractError

_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID = re.compile(r"^[0-9a-f]{16}$")
_RECEIPT_HASH = re.compile(r"^[0-9a-f]{64}$")


def new_trace_id() -> str:
    return secrets.token_hex(16)


def new_span_id() -> str:
    return secrets.token_hex(8)


@dataclass(frozen=True)
class CorrelationContext:
    """Immutable trace/receipt correlation carrier. Implements N-R4."""

    trace_id: str
    span_id: str
    receipt_hash: str | None = None
    task_id: str | None = None

    def __post_init__(self):
        if not _TRACE_ID.match(self.trace_id):
            raise ContractError("trace_id must be 32 lowercase hex chars")
        if not _SPAN_ID.match(self.span_id):
            raise ContractError("span_id must be 16 lowercase hex chars")
        if self.receipt_hash is not None and not _RECEIPT_HASH.match(self.receipt_hash):
            raise ContractError("receipt_hash must be a lowercase SHA-256 digest")

    @classmethod
    def start(cls, task_id: str | None = None) -> "CorrelationContext":
        return cls(trace_id=new_trace_id(), span_id=new_span_id(), task_id=task_id)

    def child_span(self) -> "CorrelationContext":
        """New span within the same trace (receipt binding preserved)."""
        return replace(self, span_id=new_span_id())

    def bind_receipt(self, receipt_hash: str) -> "CorrelationContext":
        if self.receipt_hash is not None and self.receipt_hash != receipt_hash:
            raise ContractError("context already bound to a different receipt")
        return replace(self, receipt_hash=receipt_hash)

    @property
    def traceparent(self) -> str:
        """W3C traceparent header value (version 00, sampled)."""
        return f"00-{self.trace_id}-{self.span_id}-01"

    @classmethod
    def from_traceparent(cls, header: str, **kw) -> "CorrelationContext":
        parts = header.split("-")
        if len(parts) != 4 or parts[0] != "00":
            raise ContractError("invalid traceparent header")
        return cls(trace_id=parts[1], span_id=parts[2], **kw)

    def log_fields(self) -> dict:
        """Fields to merge into structured log events for join-ability."""
        out = {"trace_id": self.trace_id, "span_id": self.span_id}
        if self.receipt_hash:
            out["receipt_hash"] = self.receipt_hash
        if self.task_id:
            out["task_id"] = self.task_id
        return out


class TraceReceiptIndex:
    """Bidirectional exact index between traces and receipts (N-R4)."""

    def __init__(self):
        self._trace_to_receipt: dict[str, str] = {}
        self._receipt_to_traces: dict[str, list[str]] = {}
        self._spans: dict[str, list[str]] = {}

    def record(self, context: CorrelationContext) -> None:
        if context.receipt_hash is None:
            raise ContractError("cannot index a context without a receipt binding")
        existing = self._trace_to_receipt.get(context.trace_id)
        if existing is not None and existing != context.receipt_hash:
            raise ContractError("trace_id already bound to a different receipt")
        self._trace_to_receipt[context.trace_id] = context.receipt_hash
        traces = self._receipt_to_traces.setdefault(context.receipt_hash, [])
        if context.trace_id not in traces:
            traces.append(context.trace_id)
        spans = self._spans.setdefault(context.trace_id, [])
        if context.span_id not in spans:
            spans.append(context.span_id)

    def receipt_for_trace(self, trace_id: str) -> str | None:
        return self._trace_to_receipt.get(trace_id)

    def traces_for_receipt(self, receipt_hash: str) -> list[str]:
        return list(self._receipt_to_traces.get(receipt_hash, []))

    def spans_for_trace(self, trace_id: str) -> list[str]:
        return list(self._spans.get(trace_id, []))
