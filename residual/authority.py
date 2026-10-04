"""Typed authority-coercion rejections (Track A2 emission layer).

Every authority-kernel rejection path raises `AuthorityCoercionRejected`
instead of a bare `ContractError`, so that the *reason* a denial happened
is machine-readable: which invariant's coercion boundary was crossed,
which failure code is primary, which codes triggered, and which
fail-closed state the system entered.

Fail-closed behavior is unchanged — only type information is added.
`AuthorityCoercionRejected` subclasses `ContractError`, so every existing
`except ContractError` / `pytest.raises(ContractError)` boundary keeps
working.
"""
from __future__ import annotations

from .core import ContractError

# ---------------------------------------------------------------------------
# Normative vocabulary (AUTH_INVARIANTS.md; runner design §9).
# ---------------------------------------------------------------------------

FAILURE_CODES = (
    "AMBIGUOUS_ACCEPTANCE_CONDITION",
    "UNBOUND_EVIDENCE_SOURCE",
    "UNRESOLVED_AUTHORITY",
    "UNPROVEN_ACCEPTANCE",
    "STALE_CONTRACT",
    "UNAUTHORIZED_CONTRACT_REINTERPRETATION",
    "UNAPPROVED_ACTION",
    "IMPLICIT_AUTHORITY_COERCION",
)

FAIL_CLOSED_STATES = (
    "NO_AUTHORITY_CHANGE",
    "NO_EXECUTION",
    "NO_IMPLICIT_DEFAULT",
    "NO_PROMOTION",
    "STALE_CONTRACT",
    "UNPROVEN",
)

# Fixed pipeline precedence (AUTH_INVARIANTS.md, compound-attack rule):
# the earliest-triggered invariant in this order is the primary code.
PRECEDENCE = (
    "INV-AUTH-AMB-005",
    "INV-AUTH-CTR-004",
    "INV-AUTH-IDN-002",
    "INV-AUTH-AUT-006",
    "INV-AUTH-EVD-001",
    "INV-AUTH-ACC-003",
)

CODE_TO_INVARIANT = {
    "AMBIGUOUS_ACCEPTANCE_CONDITION": "INV-AUTH-AMB-005",
    "UNAUTHORIZED_CONTRACT_REINTERPRETATION": "INV-AUTH-CTR-004",
    "STALE_CONTRACT": "INV-AUTH-CTR-004",
    "UNRESOLVED_AUTHORITY": "INV-AUTH-IDN-002",
    "UNAPPROVED_ACTION": "INV-AUTH-AUT-006",
    "UNBOUND_EVIDENCE_SOURCE": "INV-AUTH-EVD-001",
    "UNPROVEN_ACCEPTANCE": "INV-AUTH-ACC-003",
    "IMPLICIT_AUTHORITY_COERCION": "INV-AUTH-000",
}

SOURCE_TARGET = {
    "INV-AUTH-EVD-001": ("OBSERVATION", "EVIDENCE"),
    "INV-AUTH-IDN-002": ("IDENTITY", "AUTHORITY"),
    "INV-AUTH-ACC-003": ("TEST_RESULT", "ACCEPTANCE"),
    "INV-AUTH-CTR-004": ("INTERPRETATION", "CONTRACT"),
    "INV-AUTH-AMB-005": ("AMBIGUOUS_INTENT", "EXECUTABLE_AUTHORITY"),
    "INV-AUTH-AUT-006": ("SUGGESTION", "AUTHORIZATION"),
}


def _primary_code(triggered_codes: tuple[str, ...]) -> str:
    """Earliest-triggered invariant in pipeline precedence order."""
    rank = {inv: i for i, inv in enumerate(PRECEDENCE)}
    best: str | None = None
    best_rank = len(PRECEDENCE)
    for code in triggered_codes:
        inv = CODE_TO_INVARIANT.get(code)
        if inv is None or inv == "INV-AUTH-000":
            raise ValueError(f"unknown or generic code in triggered set: {code!r}")
        if rank[inv] < best_rank:
            best, best_rank = code, rank[inv]
    if best is None:  # pragma: no cover - guarded by validation below
        raise ValueError("empty triggered_codes")
    return best


class AuthorityCoercionRejected(ContractError):
    """A rejection at an AUTH coercion boundary, with its type attached.

    Attributes:
        code: primary failure code (earliest in pipeline precedence).
        triggered_codes: all triggered codes, in invariant-ID order.
        fail_closed_state: the fail-closed state the system entered.
        invariant_id: invariant of the primary code.
        reason: human-readable explanation (also the exception message).
    """

    def __init__(
        self,
        *,
        code: str,
        fail_closed_state: str,
        reason: str = "",
        triggered_codes: tuple[str, ...] | list[str] = (),
        invariant_id: str | None = None,
    ) -> None:
        if code not in FAILURE_CODES:
            raise ValueError(f"unknown failure code: {code!r}")
        if fail_closed_state not in FAIL_CLOSED_STATES:
            raise ValueError(f"unknown fail-closed state: {fail_closed_state!r}")
        triggered = tuple(triggered_codes) if triggered_codes else (code,)
        for t in triggered:
            if t not in FAILURE_CODES:
                raise ValueError(f"unknown triggered failure code: {t!r}")
        primary = _primary_code(triggered)
        # triggered_codes are stored in invariant-ID order (deterministic).
        ordered = tuple(sorted(triggered, key=lambda c: CODE_TO_INVARIANT[c]))
        self.code: str = primary
        self.triggered_codes: tuple[str, ...] = ordered
        self.fail_closed_state: str = fail_closed_state
        self.invariant_id: str = invariant_id or CODE_TO_INVARIANT[primary]
        if self.invariant_id != CODE_TO_INVARIANT[primary]:
            raise ValueError(
                f"invariant_id {self.invariant_id!r} does not match "
                f"primary code {primary!r}"
            )
        self.reason: str = reason or primary
        super().__init__(self.reason)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"AuthorityCoercionRejected(code={self.code!r}, "
            f"triggered_codes={self.triggered_codes!r}, "
            f"fail_closed_state={self.fail_closed_state!r}, "
            f"invariant_id={self.invariant_id!r})"
        )
