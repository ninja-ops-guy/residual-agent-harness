"""WebVM build entry point using the hardened browser mailbox transport."""
from __future__ import annotations

import base64
from pathlib import Path
import signal

from residual.core import ContractError, canonical
from . import conversation_build as implementation
from .browser_mailbox import BrowserMailboxProvider
from .runner import FRAME

# Keep the authoritative task/verifier/evidence implementation unchanged;
# inject only the browser mailbox transport into this WebVM entry point.


def main(argv=None):
    """Standalone CLI behavior remains the existing bounded user-facing contract."""
    return implementation.main(argv, mailbox_provider_type=BrowserMailboxProvider)


def persistent_build(*, request: dict, mailbox: Path, root: Path, output_root: Path) -> int:
    """Execute the already-admitted build request while preserving fatal errors."""
    request = {**request, 'mode': 'build'}

    def stream(event):
        raw = canonical(event).encode()
        if len(raw) > implementation.MAX_RESULT:
            raise ContractError('projection exceeds byte budget')
        print(FRAME + base64.urlsafe_b64encode(raw).decode() + '\x07', flush=True)

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
                'Iterative build failed: check provider consent, parent evidence, budget, or workspace lock. No success claimed.',
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
        'semantic_verification': 'UNKNOWN',
        'generated_files': summary['generated_files'],
        'lineage': summary['lineage'],
    }))
    return 0 if summary['result']['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
