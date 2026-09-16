"""WebVM build entry point using the hardened browser mailbox transport."""
from __future__ import annotations

from . import conversation_build as implementation
from .browser_mailbox import BrowserMailboxProvider

# conversation_build resolves this module global at execution time. Keep the
# authoritative task/verifier/evidence implementation unchanged; replace only
# the browser mailbox transport used by this WebVM entry point.
implementation.MailboxProvider = BrowserMailboxProvider


def main(argv=None):
    return implementation.main(argv)


if __name__ == '__main__':
    raise SystemExit(main())
