"""Host-side constants for the M4 isolated-child wire/exit protocol.

This module must remain platform-neutral. The Linux-only _isolated_child.py
mirrors these literal values because it executes as a standalone script and
must not import the residual.factory package before namespace setup.
"""

SANDBOX_ERROR_PREFIX = "M4SANDBOX-ERROR:"
SANDBOX_ERROR_EXIT = 125
SANDBOX_TIMEOUT_EXIT = 124
