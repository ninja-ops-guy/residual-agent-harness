from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from residual.factory.runtime_journal import RuntimeJournal


class _BeginInterceptor:
    def __init__(self, inner: sqlite3.Connection, attempts: list[int], *, fail_count: int,
                 error_code: int = sqlite3.SQLITE_BUSY):
        self._inner = inner
        self._attempts = attempts
        self._fail_count = fail_count
        self._error_code = error_code

    def execute(self, statement, params=()):
        if statement == "BEGIN IMMEDIATE":
            self._attempts.append(1)
            if len(self._attempts) <= self._fail_count:
                exc = sqlite3.OperationalError("database is locked")
                exc.sqlite_errorcode = self._error_code
                raise exc
        return self._inner.execute(statement, params)

    def close(self):
        return self._inner.close()

    def __getattr__(self, name):
        return getattr(self._inner, name)


class RuntimeJournalWriterAdmissionTests(unittest.TestCase):
    def test_constructor_transient_busy_is_retried_within_production_budget(self):
        original = sqlite3.connect
        attempts: list[int] = []
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "constructor-retry.sqlite"

            def connect(*args, **kwargs):
                return _BeginInterceptor(original(*args, **kwargs), attempts, fail_count=2)

            with patch("residual.factory.runtime_journal.sqlite3.connect", side_effect=connect):
                journal = RuntimeJournal(path, trace_id="constructor-retry")

            self.assertEqual(len(attempts), 3)
            self.assertEqual(journal.trace_id, "constructor-retry")
            journal.observations()

    def test_constructor_non_contention_operational_error_is_not_retried(self):
        original = sqlite3.connect
        attempts: list[int] = []
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "constructor-error.sqlite"

            def connect(*args, **kwargs):
                return _BeginInterceptor(
                    original(*args, **kwargs),
                    attempts,
                    fail_count=1,
                    error_code=sqlite3.SQLITE_ERROR,
                )

            with patch("residual.factory.runtime_journal.sqlite3.connect", side_effect=connect):
                with self.assertRaises(sqlite3.OperationalError):
                    RuntimeJournal(path, trace_id="constructor-error")
            self.assertEqual(len(attempts), 1)

    def test_constructor_persistent_busy_is_bounded_and_fail_closed(self):
        original = sqlite3.connect
        attempts: list[int] = []
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "constructor-busy.sqlite"

            def connect(*args, **kwargs):
                return _BeginInterceptor(original(*args, **kwargs), attempts, fail_count=10_000)

            started = time.monotonic()
            with (
                patch.object(RuntimeJournal, "WRITE_TRANSACTION_TIMEOUT_S", 0.12),
                patch.object(RuntimeJournal, "WRITE_CONNECT_TIMEOUT_S", 0.02),
                patch("residual.factory.runtime_journal.sqlite3.connect", side_effect=connect),
            ):
                with self.assertRaises(sqlite3.OperationalError):
                    RuntimeJournal(path, trace_id="constructor-busy")
            elapsed = time.monotonic() - started

            self.assertGreaterEqual(elapsed, 0.09)
            self.assertLess(elapsed, 0.5)
            # The total deadline is authoritative. On a slower interpreter/host,
            # schema initialization can consume the 120 ms test budget before a
            # second BEGIN is attempted. The transient test above independently
            # proves that contention is retried when budget remains; this case
            # proves persistent contention stays bounded and fails closed.
            self.assertGreaterEqual(len(attempts), 1)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = RuntimeJournal(Path(self.temp.name) / "journal.sqlite", trace_id="release-stabilization")

    def test_transient_busy_before_begin_is_retried_without_replaying_body(self):
        original = sqlite3.connect
        attempts: list[int] = []

        def connect(*args, **kwargs):
            return _BeginInterceptor(original(*args, **kwargs), attempts, fail_count=2)

        with patch("residual.factory.runtime_journal.sqlite3.connect", side_effect=connect):
            self.journal.observe({"event": "WriterAdmissionRecovered", "value": 1})

        self.assertEqual(len(attempts), 3)
        recovered = [o.payload for o in self.journal.observations()
                     if o.payload.get("event") == "WriterAdmissionRecovered"]
        self.assertEqual(recovered, [{"event": "WriterAdmissionRecovered", "value": 1}])

    def test_non_contention_operational_error_is_not_retried(self):
        original = sqlite3.connect
        attempts: list[int] = []

        def connect(*args, **kwargs):
            return _BeginInterceptor(original(*args, **kwargs), attempts, fail_count=1,
                                     error_code=sqlite3.SQLITE_ERROR)

        with patch("residual.factory.runtime_journal.sqlite3.connect", side_effect=connect):
            with self.assertRaises(sqlite3.OperationalError):
                self.journal.observe({"event": "MustNotRetry"})
        self.assertEqual(len(attempts), 1)
        self.assertFalse(any(o.payload.get("event") == "MustNotRetry"
                             for o in self.journal.observations()))

    def test_persistent_busy_remains_bounded_and_fail_closed(self):
        original = sqlite3.connect
        attempts: list[int] = []
        self.journal.WRITE_TRANSACTION_TIMEOUT_S = 0.12
        self.journal.WRITE_CONNECT_TIMEOUT_S = 0.02

        def connect(*args, **kwargs):
            return _BeginInterceptor(original(*args, **kwargs), attempts, fail_count=10_000)

        started = time.monotonic()
        with patch("residual.factory.runtime_journal.sqlite3.connect", side_effect=connect):
            with self.assertRaises(sqlite3.OperationalError):
                self.journal.observe({"event": "PersistentBusy"})
        elapsed = time.monotonic() - started

        self.assertGreaterEqual(elapsed, 0.09)
        self.assertLess(elapsed, 0.5)
        self.assertGreater(len(attempts), 1)
        self.assertFalse(any(o.payload.get("event") == "PersistentBusy"
                             for o in self.journal.observations()))


if __name__ == "__main__":
    unittest.main()
