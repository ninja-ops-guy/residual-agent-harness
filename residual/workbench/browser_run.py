"""WebVM review/audit entry point using the hardened browser mailbox transport."""
from __future__ import annotations

from . import runner as implementation
from .browser_mailbox import BrowserMailboxProvider

implementation.MailboxProvider = BrowserMailboxProvider


def main(argv=None):
    return implementation.main(argv)


if __name__ == '__main__':
    raise SystemExit(main())
