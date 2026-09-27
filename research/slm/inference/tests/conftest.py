"""Test fixtures: make the repo root importable from any checkout depth."""

import os
import sys

# tests/ -> inference/ -> slm/ -> research/ -> <repo root>
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
