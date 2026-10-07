"""WebVM review/audit entry point using the hardened browser mailbox transport."""
from __future__ import annotations

import base64
from pathlib import Path
import signal

from residual.core import ContractError, canonical
from . import runner as implementation
from .browser_mailbox import BrowserMailboxProvider



def main(argv=None):
    """Standalone CLI behavior remains the existing bounded user-facing contract."""
    return implementation.main(argv, mailbox_provider_type=BrowserMailboxProvider)


def persistent_run(*, request: dict, mailbox: Path, root: Path, output_root: Path) -> int:
    """Execute the already-admitted request without masking runtime exceptions.

    Admission reads and validates the request once in browser_worker. Reusing that
    exact object avoids a second parse / request-file TOCTOU between identity
    validation and execution. Do not catch TypeError/ValueError/OSError here:
    retained corruption has surfaced as impossible TypeErrors inside CPython and
    must escape so the persistent worker is poisoned and restarted.
    """
    def stream(event):
        raw = canonical(event).encode()
        if len(raw) > implementation.MAX_RESULT:
            raise ContractError('projection exceeds byte budget')
        print(implementation.FRAME + base64.urlsafe_b64encode(raw).decode() + '\x07', flush=True)

    def deadline(_signum, _frame):
        raise implementation.WorkbenchDeadline('mission wall-clock budget exhausted')

    previous = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(240)
    try:
        try:
            summary = implementation.execute(
                request,
                root=root,
                output_root=output_root,
                mailbox=mailbox,
                config=None,
                observer=stream,
                mailbox_provider_type=BrowserMailboxProvider,
            )
        except (ContractError, implementation.WorkbenchDeadline):
            print(
                'Mission failed: check source paths, consent/provider connection, budget, or workspace lock. No success claimed.',
                file=implementation.sys.stderr,
            )
            return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)

    print(canonical({
        'status': summary['status'],
        'output': summary['output'],
        'simulation': False,
        'semantic_verification': summary['semantic_verification'],
    }))
    return 0 if summary['result']['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
