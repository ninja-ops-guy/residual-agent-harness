"""Bounded-cardinality label sanitization (OBS-R3).

Metric labels MUST avoid unbounded task/content cardinality by default.
Label values are folded through an explicit allowlist; anything not in the
allowlist maps to the overflow bucket. Forbidden keys (task ids, content
ids, prompts, payloads) are rejected outright and never reach a label.
"""
from __future__ import annotations

from .schema import (
    DEFAULT_LABEL_ALLOWLIST,
    FORBIDDEN_LABEL_KEYS,
    OVERFLOW_BUCKET,
)


class LabelCardinalityError(ValueError):
    """Raised when a forbidden high-cardinality label key is used."""


class LabelSanitizer:
    """Folds label values into bounded allowlists with an overflow bucket."""

    def __init__(self, allowlist=None, forbidden_keys=None, max_distinct_per_key: int = 64):
        self._allowlist = dict(allowlist or DEFAULT_LABEL_ALLOWLIST)
        self._forbidden = set(forbidden_keys or FORBIDDEN_LABEL_KEYS)
        self._max_distinct = max_distinct_per_key
        self._overflowed = {}  # key -> count of values folded into overflow

    def sanitize(self, labels: dict) -> dict:
        """Return a {key: value} mapping with bounded cardinality per key."""
        out = {}
        for key, value in sorted(labels.items()):
            if key in self._forbidden:
                raise LabelCardinalityError(
                    f"label key {key!r} is forbidden (unbounded cardinality risk)"
                )
            allowed = self._allowlist.get(key)
            value = str(value)
            if allowed is None:
                # Key has no explicit allowlist: bound it via max-distinct tracking.
                seen = self._overflowed.setdefault(f"__seen__:{key}", set())
                if value not in seen:
                    if len(seen) >= self._max_distinct:
                        self._overflowed[key] = self._overflowed.get(key, 0) + 1
                        value = OVERFLOW_BUCKET
                    else:
                        seen.add(value)
            elif value not in allowed:
                self._overflowed[key] = self._overflowed.get(key, 0) + 1
                value = OVERFLOW_BUCKET
            out[key] = value
        return out

    def overflow_counts(self) -> dict:
        """How many values were folded into the overflow bucket, per key."""
        return {k: v for k, v in self._overflowed.items() if not k.startswith("__seen__:")}
