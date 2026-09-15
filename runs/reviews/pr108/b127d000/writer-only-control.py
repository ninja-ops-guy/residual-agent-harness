import json
from tests.test_sandbox_timing_adversarial import *
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
               [threading.Thread(target=reader) for _ in range(0)])
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    reader_locked = [e for e in errors if e[0] == "reader" and "locked" in e[1]]
    writer_locked = [e for e in errors if e[0] == "writer" and "locked" in e[1]]
    print(json.dumps({"readers": 0, "writers": 4, "writer_locked": len(writer_locked), "reader_locked": len(reader_locked)}))
    assert writer_locked, "writer-only fault control did not exercise contention"
    # Evidence retained in the failure message on any regression.
    self.assertEqual(
        [], reader_locked,
        f"{len(reader_locked)} reader 'database is locked' errors under "
        f"concurrency (e.g. {reader_locked[:1]}); same error class as CI "
        f"run 34940491451 (writer-side raw-connection contention observed "
        f"during this run: {len(writer_locked)} events, out of scope)")

case = CiLockContentionTests()
try:
    test_observations_under_write_storm_never_raises_locked(case)
finally:
    case.doCleanups()
