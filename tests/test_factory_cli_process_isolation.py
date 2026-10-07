"""Adversarial coverage for parent-process noise at the real CLI boundary."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import warnings

from tests import test_factory_runtime_lifecycle as lifecycle


class CLIProcessIsolationTests(unittest.TestCase):
    def test_parent_warning_does_not_enter_cli_json_for_either_alias(self):
        case = lifecycle.LifecycleGuards(
            'test_missing_cli_input_returns_sanitized_blocked_json_for_both_run_aliases')
        case.setUp()
        self.addCleanup(case.doCleanups)
        real_read = Path.read_text
        real_run = subprocess.run
        emitted = []
        marker = 'unrelated parent interpreter resource warning'

        def noise():
            emitted.append(marker)
            warnings.warn(marker, ResourceWarning)

        def parent_read(path, *args, **kwargs):
            # Also exercises the previous in-process implementation: there,
            # this unrelated warning corrupts its global stderr capture.
            if path == case.root / 'missing.json':
                noise()
            return real_read(path, *args, **kwargs)

        def parent_run(argv, *args, **kwargs):
            if argv[1:3] == ['-m', 'residual.factory']:
                noise()
            return real_run(argv, *args, **kwargs)

        def show_warning(message, category, filename, lineno, file=None, line=None):
            # Match default warning emission even when pytest installs its own
            # warning collector. The subprocess inherits neither this hook nor
            # the parent's injected warning.
            stream = sys.stderr if file is None else file
            stream.write(warnings.formatwarning(message, category, filename, lineno, line))

        parent_stderr = io.StringIO()
        with warnings.catch_warnings():
            warnings.simplefilter('always', ResourceWarning)
            with redirect_stderr(parent_stderr), \
                 patch.object(warnings, 'showwarning', show_warning), \
                 patch.object(Path, 'read_text', parent_read), \
                 patch.object(subprocess, 'run', parent_run):
                case.test_missing_cli_input_returns_sanitized_blocked_json_for_both_run_aliases()
        self.assertEqual(emitted, [marker, marker])
        self.assertEqual(parent_stderr.getvalue().count('ResourceWarning: ' + marker), 2)
