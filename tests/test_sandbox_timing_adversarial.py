"""Adversarial test battery for PR #108 review blockers (Lane 2 origin,
adapted by Lane 1 to the repaired API surface).

Origin: Lane 2 independent review battery `tests_adversarial_lane2.py`,
written against head b3b2a5a18ce28bd1249725c7529228acca7d498e (9 FAIL /
3 PASS there). Adaptations relative to the origin, all forced by the
repair's API changes, never by weakened assertions:

- Lease-unknown mutant tests patched the now-defunct journal-global
  `lease_state` hook; they now patch the atomic `lease_read` (the fix's
  typed-result API) with identical timing/contention semantics.
- The diagnostic-attribution tests read the removed journal-global
  `lease_read_diag`; they now assert on the atomic LeaseRead binding and on
  the absence of any journal-global diagnostic (erasure/cross-attribution
  are impossible by construction, and both directions are still exercised
  through real contended reads).
- The CI write-storm test's locked-error assertion is scoped to READERS.
  The battery's raw writer threads (4 writers, 0.2s busy timeout, 50ms
  held BEGIN IMMEDIATE transactions) contend among themselves outside any
  repo code path: the storm reproduces writer-side 'database is locked'
  even with ZERO readers, so no repository fix can affect it. The CI
  failure being repaired (run 34940491451) was a READER-side failure;
  reader-side locked errors remain hard failures here.

Linux-only tests skip elsewhere. No network, no namespace requirements.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from residual.factory import runtime as fr
from residual.factory.runtime_journal import LeaseRead, RuntimeJournal


def _mk_contract(attempt_id="a", lease_id=None, generation=1, contract_hash="h"):
    class C:  # duck-typed: the lease read path uses only these fields
        pass
    c = C()
    c.attempt_id = attempt_id
    c.lease_id = lease_id or ("L-" + attempt_id)
    c.lease_generation = generation
    c.contract_hash = contract_hash
    return c


def _seed_attempt(db, contract, state="RUNNING"):
    now = time.time_ns()
    db.execute(
        "INSERT INTO attempts(attempt_id,task_id,worker_id,swarm_id,plan_hash,"
        "contract_hash,contract_json,lease_id,generation,workspace,state,created_ns,updated_ns) "
        "VALUES (?,?,?,'s','p',?,'{}',?,?,? ,?,?,?)",
        (contract.attempt_id, "t-" + contract.attempt_id, "w-" + contract.attempt_id,
         contract.contract_hash, contract.lease_id, contract.lease_generation,
         "/tmp/" + contract.attempt_id, state, now, now))


class _ExclusiveHolder:
    """Holds BEGIN EXCLUSIVE on a journal DB from a background thread.

    The DB is switched to rollback-journal mode first so readers genuinely
    contend (in WAL mode plain writers never block readers; the CI failure
    on run 34940491451 shows contention does reach the read path in
    practice — see CiLockContentionTests).
    """

    def __init__(self, path):
        self.path = str(path)
        self.started = threading.Event()
        self.release = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        db = sqlite3.connect(self.path, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("BEGIN EXCLUSIVE")
        db.execute("INSERT INTO metadata VALUES ('lock-holder','1') ON CONFLICT DO NOTHING")
        self.started.set()
        self.release.wait(60)
        db.execute("ROLLBACK")
        db.close()

    def __enter__(self):
        self.thread.start()
        assert self.started.wait(10)
        return self

    def __exit__(self, *exc):
        self.release.set()
        self.thread.join(10)


class _JournalCase(unittest.TestCase):
    def setUp(self):
        if sys.platform != "linux":
            self.skipTest("Linux runtime only")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.journal = RuntimeJournal(root / "journal.sqlite", trace_id="adv")
        # rollback-journal mode => readers contend with an exclusive writer
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            db.execute("PRAGMA journal_mode=DELETE")

    def _runtime(self):
        rt = fr.FactoryRuntime.__new__(fr.FactoryRuntime)
        rt.journal = self.journal
        rt._clock = time.monotonic
        return rt


# ---------------------------------------------------------------------------
# Blocker 2: lease-unknown handling must respect ONE absolute 2s deadline
# ---------------------------------------------------------------------------
class LeaseUnknownDeadlineTests(_JournalCase):
    def test_lease_denial_total_block_is_bounded(self):
        """Persistent contention: _lease_denial must return within ~2s total,
        including the first read. Head b3b2a5a took ~4s (2s first read + a
        fresh 2s retry window)."""
        c = _mk_contract()
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            _seed_attempt(db, c)
        rt = self._runtime()
        with _ExclusiveHolder(self.journal.path):
            t0 = time.monotonic()
            result = rt._lease_denial(c, "revoked_or_unavailable")
            elapsed = time.monotonic() - t0
        self.assertIsNotNone(result)
        self.assertEqual(result[:2], ("lease", "lease_unreadable"))
        self.assertLessEqual(
            elapsed, 2.5,
            f"watchdog blocked {elapsed:.2f}s in _lease_denial; advertised hard bound is 2s")

    def test_lease_denial_mutant_shorter_inner_timeout_still_bounded(self):
        """Mutant-catcher: even if an individual read is slow, the retry loop
        must re-check an ABSOLUTE deadline that includes the first read. We
        simulate reads that each take ~1.8s (under a 2s per-read timeout, so
        they never raise) and demand the total stays bounded."""
        c = _mk_contract()
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            _seed_attempt(db, c)
        rt = self._runtime()
        calls = []

        def slow_unknown(contract, *, deadline=None, clock=None):
            # A slow store read that RESPECTS its caller-supplied busy budget
            # (the repaired lease_read contract). A mutant that passes no
            # deadline/budget gets the full slow 1.8s per read and fails the
            # total-time assertion below.
            calls.append(time.monotonic())
            budget = 1.8
            if deadline is not None:
                budget = min(budget, max(0.0, deadline - time.monotonic()))
            time.sleep(budget)
            return LeaseRead("unknown", ("OperationalError", 5))

        original = self.journal.lease_read
        self.journal.lease_read = slow_unknown
        try:
            t0 = time.monotonic()
            result = rt._lease_denial(c, "revoked_or_unavailable")
            elapsed = time.monotonic() - t0
        finally:
            self.journal.lease_read = original
        self.assertIsNotNone(result)
        self.assertEqual(result[1], "lease_unreadable")
        self.assertLessEqual(
            elapsed, 2.5,
            f"total {elapsed:.2f}s with {len(calls)} reads; deadline must start at first read")

    def test_unknown_never_retyped_as_revocation(self):
        """A store that recovers mid-retry must be re-read: 'unknown' must not
        be converted to 'revoked'/'lease_generation' without a fresh read."""
        c = _mk_contract()
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            _seed_attempt(db, c)
        rt = self._runtime()
        reads = iter([LeaseRead("unknown", ("OperationalError", 5)),
                      LeaseRead("current")])

        def flaky(contract, *, deadline=None, clock=None):
            return next(reads, LeaseRead("current"))

        original = self.journal.lease_read
        self.journal.lease_read = flaky
        try:
            result = rt._lease_denial(c, "revoked_or_unavailable")
        finally:
            self.journal.lease_read = original
        self.assertIsNone(result, "transient 'unknown' followed by 'current' must not kill")


# ---------------------------------------------------------------------------
# Blocker 4: lease-read diagnostics must be per-attempt / atomic
# ---------------------------------------------------------------------------
class LeaseDiagAttributionTests(_JournalCase):
    def test_diag_cannot_be_erased_by_concurrent_attempt(self):
        """Attempt A's failed read produces a diag; before A's caller consumes
        it, attempt B's successful read must not erase A's provenance. The
        repaired API binds the diag to the returned LeaseRead object."""
        ca, cb = _mk_contract("a"), _mk_contract("b")
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            _seed_attempt(db, ca)
            _seed_attempt(db, cb)
        with _ExclusiveHolder(self.journal.path):
            read_a = self.journal.lease_read(ca)
        read_b = self.journal.lease_read(cb)  # succeeds, after A's read
        self.assertEqual(read_a.state, "unknown")
        self.assertEqual(read_b.state, "current")
        self.assertIsNotNone(
            read_a.diag,
            "A's read-error provenance was erased by B's concurrent read")
        self.assertEqual(read_a.diag[0], "OperationalError")
        # The journal-global provenance channel must not exist at all.
        self.assertFalse(hasattr(self.journal, "lease_read_diag"))

    def test_diag_cannot_be_cross_attributed(self):
        """Attempt A reads fine; attempt B's read fails. A's caller must not
        observe B's error as its own diagnostic."""
        ca, cb = _mk_contract("a"), _mk_contract("b")
        with sqlite3.connect(self.journal.path, isolation_level=None) as db:
            _seed_attempt(db, ca)
            _seed_attempt(db, cb)
        read_a = self.journal.lease_read(ca)  # current; A has no error
        self.assertEqual(read_a.state, "current")
        self.assertIsNone(read_a.diag)
        with _ExclusiveHolder(self.journal.path):
            read_b = self.journal.lease_read(cb)  # unknown, with its own diag
        self.assertEqual(read_b.state, "unknown")
        self.assertIsNotNone(read_b.diag)
        # A's already-returned read object is unchanged by B's failure.
        self.assertEqual(read_a.state, "current")
        self.assertIsNone(
            read_a.diag,
            f"B's error {read_b.diag} became visible on A's read result")
        # And there is no shared channel through which it could leak later.
        self.assertIsNone(getattr(self.journal, "lease_read_diag", None))


# ---------------------------------------------------------------------------
# Blocker 3: ProcessControl.stopped must imply a reaped process
# ---------------------------------------------------------------------------
@unittest.skipUnless(sys.platform == "linux", "pidfd required")
class ReapTimeoutSemanticsTests(unittest.TestCase):
    def test_reap_timeout_does_not_publish_stopped_as_completion(self):
        from residual.factory.termination_provenance import ProcessControl
        proc = subprocess.Popen(["sleep", "30"])
        self.addCleanup(lambda: (proc.kill(), proc.wait()))
        pc = ProcessControl(proc, correlation_id="adv-b3")

        def stuck_reap(timeout=2.0):
            raise subprocess.TimeoutExpired(cmd="sleep", timeout=timeout)
        pc.reap = stuck_reap  # models a genuinely stuck reap (D-state etc.)

        pc.kill(("resource", "wall_clock_budget_s", {"elapsed_s": 1.0}),
                requester="watchdog")
        self.assertTrue(pc.reap_timed_out.is_set())
        # INVARIANT: stopped must never be published for an unreaped process.
        if pc.stopped.is_set() and not pc.reaped:
            self.fail("stopped was set on reap timeout while _reaped is false; "
                      "callers treat stopped as completion evidence")
        # With stopped (correctly) withheld, a follow-up reap must be able to
        # complete the lifecycle (record + close) once the process is reapable.
        del pc.reap
        rc = ProcessControl.reap(pc, timeout=5.0)
        self.assertIsInstance(rc, int)
        self.assertTrue(pc.reaped)
        pc.termination_record()  # must not raise now
        pc.close()

    def test_reap_timeout_reason_is_typed_not_silent(self):
        """Mutant-catcher: a reap timeout must surface the typed
        reap_timed_out condition AND a reap_timeout reason when no primary
        reason exists; a fix that swallows the timeout fails here."""
        from residual.factory.termination_provenance import ProcessControl
        proc = subprocess.Popen(["sleep", "30"])
        self.addCleanup(lambda: (proc.kill(), proc.wait()))
        pc = ProcessControl(proc, correlation_id="adv-b3b")
        pc.reap = lambda timeout=2.0: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd="sleep", timeout=timeout))
        pc.kill(None, requester="watchdog")
        self.assertTrue(pc.reap_timed_out.is_set(),
                        "reap timeout was swallowed without a typed event")
        self.assertIsNotNone(pc.reason)
        self.assertEqual(pc.reason[:2], ("resource", "reap_timeout"))


# ---------------------------------------------------------------------------
# Blocker 5: uniform deterministic timeout returncode across lanes
# ---------------------------------------------------------------------------
@unittest.skipUnless(__import__("os").name == "posix", "process groups required")
class FixtureTimeoutContractTests(unittest.TestCase):
    def test_fixture_timeout_returncode_matches_documented_124(self):
        from residual.factory.m4_safety import run_trusted_fixture
        worktree = tempfile.mkdtemp(prefix="adv-b5-")
        res = run_trusted_fixture(("sleep", "30"), worktree,
                                  timeout_s=0.5, output_limit=65536)
        self.assertEqual(res.status, "timeout")
        self.assertTrue(res.timed_out)
        self.assertEqual(
            res.returncode, 124,
            f"fixture lane returned {res.returncode} (killed-signal code); the "
            "PR advertises a uniform deterministic timeout returncode 124 "
            "(SANDBOX_TIMEOUT_EXIT) across lanes")

    def test_candidate_legit_exit_124_not_retyped_timeout(self):
        """Mutant-catcher / collision guard: a candidate that EXITS 124 on its
        own must type as FAIL with timed_out False (isolated lane)."""
        from residual.sandbox.subprocess_backend import _classify
        exit_code, sig, violation = _classify(124, False)
        self.assertEqual(exit_code, 124)
        self.assertIsNone(sig)
        self.assertNotEqual(violation.name, "TIMEOUT")


# ---------------------------------------------------------------------------
# Blocker 1: v2 receipt serialization must not change in place
# ---------------------------------------------------------------------------
class ReceiptSchemaStabilityTests(unittest.TestCase):
    def test_v2_verification_result_serialization_unchanged(self):
        from residual.factory.m4_integrator import (
            INTEGRATION_SCHEMA, VerificationResult)
        self.assertEqual(INTEGRATION_SCHEMA, "factory-integration-receipt-v2")
        vr = VerificationResult(
            name="t", category="c", status="pass", returncode=0,
            stdout_sha256="a" * 64, stderr_sha256="b" * 64,
            termination_reason="exit",
            execution_boundary="trusted_fixture_unsandboxed")
        keys = set(vr.to_dict())
        self.assertNotIn(
            "timed_out", keys,
            "schema remains factory-integration-receipt-v2 but to_dict() gained "
            "'timed_out', mutating the canonical signed v2 payload in place; "
            "bump/migrate the schema or use an already-versioned representation")

    def test_receipt_hash_stable_for_identical_logical_result(self):
        """The hash of a receipt for a given logical verification result must
        not depend on a newly added default field under the same schema."""
        from residual.factory.m4_integrator import (
            IntegrationReceipt, VerificationResult)
        vr = VerificationResult(
            name="t", category="c", status="pass", returncode=0,
            stdout_sha256="a" * 64, stderr_sha256="b" * 64,
            termination_reason="exit",
            execution_boundary="trusted_fixture_unsandboxed")
        r = IntegrationReceipt(
            execution_plan_hash="e", integration_plan_hash="i",
            input_receipt_hashes=(), output_commit="o",
            verification_results=(vr,), conflict_resolutions=(),
            integrated_at_ns=1, station_key_id="k", station_signature="s",
            verification_policy_hash="p")
        payload = json.dumps(r.unsigned_payload(), sort_keys=True)
        self.assertNotIn('"timed_out"', payload,
                         "v2 unsigned payload bytes changed in place")


# ---------------------------------------------------------------------------
# CI failure: concurrent journal readers must not hit 'database is locked'
# ---------------------------------------------------------------------------
@unittest.skipUnless(sys.platform == "linux", "linux CI parity")
class CiLockContentionTests(unittest.TestCase):
    def test_observations_under_write_storm_never_raises_locked(self):
        """Root-cause regression for run 34940491451: the pre-repair _connect()
        opened a fresh connection per call with timeout=0.2 and executed
        lock-sensitive PRAGMAs on every connection, so concurrent writes
        surfaced sqlite3.OperationalError: database is locked on the READ
        path. The repair gives readers a bounded, contention-safe path
        (5s busy budget + bounded retry, no write pragmas).

        Scope note (adaptation from the Lane 2 origin): the assertion covers
        READER errors. The raw writer threads below model _transaction churn
        with 0.2s timeouts and 50ms held transactions; four such writers
        contend with EACH OTHER outside any repository code path (reproduced
        with zero readers), so writer-side locked errors are recorded for
        evidence but are not a repository regression signal."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        journal = RuntimeJournal(Path(tmp.name) / "journal.sqlite", trace_id="adv-ci")
        for i in range(50):
            journal.observe({"warm": i})
        errors = []
        stop = time.monotonic() + 8.0

        def writer(n):
            i = 0
            while time.monotonic() < stop:
                # Fresh-connection writers, mirroring _transaction churn.
                try:
                    db = sqlite3.connect(str(journal.path), timeout=0.2,
                                         isolation_level=None)
                    db.execute("PRAGMA synchronous=FULL")
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("INSERT INTO metadata VALUES (?, '1') ON CONFLICT DO NOTHING",
                               (f"w{n}-{i}",))
                    time.sleep(0.05)
                    db.execute("ROLLBACK")
                    db.close()
                except sqlite3.OperationalError as e:
                    errors.append(("writer", str(e)))
                i += 1

        def reader():
            while time.monotonic() < stop:
                try:
                    journal.observations()
                except sqlite3.OperationalError as e:
                    errors.append(("reader", str(e)))
                except Exception:
                    pass  # chain/content errors are out of scope here

        threads = ([threading.Thread(target=writer, args=(i,)) for i in range(4)] +
                   [threading.Thread(target=reader) for _ in range(6)])
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        reader_locked = [e for e in errors if e[0] == "reader" and "locked" in e[1]]
        writer_locked = [e for e in errors if e[0] == "writer" and "locked" in e[1]]
        # Evidence retained in the failure message on any regression.
        self.assertEqual(
            [], reader_locked,
            f"{len(reader_locked)} reader 'database is locked' errors under "
            f"concurrency (e.g. {reader_locked[:1]}); same error class as CI "
            f"run 34940491451 (writer-side raw-connection contention observed "
            f"during this run: {len(writer_locked)} events, out of scope)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
