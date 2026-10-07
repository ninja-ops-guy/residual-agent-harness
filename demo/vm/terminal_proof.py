"""Pure helpers for parsing terminal proof markers in browser acceptance."""
from __future__ import annotations

import re

PROOF_TERMINATOR = ":END"


def proof_pattern(prefix: str) -> re.Pattern[str]:
    """Match a bounded exit code followed by the explicit proof terminator."""
    return re.compile(re.escape(prefix) + r"(\d+)" + re.escape(PROOF_TERMINATOR))


def parse_exit_marker(body: str, prefix: str) -> tuple[str, int]:
    """Parse one proof marker after ignoring terminal wrapping whitespace.

    The explicit nonnumeric terminator prevents a real ``:0`` from becoming a
    synthetic ``:03`` when narrow-terminal rendering places an unrelated digit
    after whitespace that is removed for line-wrap tolerance.
    """
    normalized = re.sub(r"\s", "", body)
    match = proof_pattern(prefix).search(normalized)
    if match is None:
        raise AssertionError("guest exit marker disappeared")
    return match.group(0), int(match.group(1))
