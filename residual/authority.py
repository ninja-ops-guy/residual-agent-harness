"""Compatibility exports for typed authority-coercion rejections.

The canonical definitions live in residual.core so exported Open Core
modules can depend on them without crossing the open-core import boundary.
"""
from __future__ import annotations

from .core import (
    AuthorityCoercionRejected,
    CODE_TO_INVARIANT,
    FAIL_CLOSED_STATES,
    FAILURE_CODES,
    PRECEDENCE,
    SOURCE_TARGET,
    _primary_code,
)
