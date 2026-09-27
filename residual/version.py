"""Single source of runtime package-version reporting."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


_PACKAGE = "residual-agent-harness"


def current_version() -> str:
    try:
        return version(_PACKAGE)
    except PackageNotFoundError:
        return "0+unknown"


__version__ = current_version()
