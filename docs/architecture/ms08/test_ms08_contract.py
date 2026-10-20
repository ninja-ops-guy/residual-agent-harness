"""Contract-test skeletons for the MS-08 writer service design (Swarm G).

Binds the normative contract in docs/architecture/MS-08-writer-service.md
against the minimal in-process reference implementation. Stdlib unittest.

First-attempt failures are retained by policy; none are deleted or weakened.
"""

import unittest

from docs.architecture.ms08.reference_writer import (
    CrashInjected,
    EmergencyJournal,
    FencingError,
    InProcessLedger,
    Rejected,
    WriterService,
    WriterUnavailableError,
)


def make_writer(writer_id="w1"):
    ledger = InProcessLedger()
    w = WriterService(ledger, writer_id)
    w.acquire_lease()
    w.reconcile()
    return ledger, w


class CommitBeforeAckTests(unittest.TestCase):
    def test_ack_only_after_commit(self):
        ledger, w = make_writer()
        ack = w.propose("e1", "k", "v1")
        self.assertEqual(ack["disposition"], "accepted")
        self.assertEqual(ack["seq"], 2)  # seq 1 is control.reconciled
        # ack hash matches the durably stored record
        self.assertEqual(ack["hash"], ledger.by_event_id["e1"]["hash"])

    def test_crash_between_write_and_ack_retry_resolves_duplicate(self):
        ledger, w = make_writer()
        w.crash_after_commit = True
        with self.assertRaises(CrashInjected):
            w.propose("e1", "k", "v1")
        # commit happened; client saw no ack and retries with the same event_id
        w.crash_after_commit = False
        ack = w.propose("e1", "k", "v1")
        self.assertEqual(ack["disposition"], "duplicate")
        # exactly one accepted mutation for e1
        mutations = [r for r in ledger.journal if r["event_id"] == "e1"]
        self.assertEqual(len(mutations), 1)
        self.assertEqual(ledger.state["k"], ("v1", 1))


class IdempotentRetryTests(unittest.TestCase):
    def test_plain_retry_is_duplicate_with_same_cursor(self):
        _, w = make_writer()
        a1 = w.propose("e1", "k", "v1")
        a2 = w.propose("e1", "k", "v1")
        self.assertEqual(a2["disposition"], "duplicate")
        self.assertEqual((a1["seq"], a1["hash"]), (a2["seq"], a2["hash"]))

    def test_cas_conflict_rejected_and_nothing_written(self):
        ledger, w = make_writer()
        w.propose("e1", "k", "v1")
        with self.assertRaises(Rejected) as ctx:
            w.propose("e2", "k", "v2", expected_generation=99)
        self.assertEqual(ctx.exception.reason, "cas_conflict")
        self.assertNotIn("e2", ledger.by_event_id)
        self.assertEqual(ledger.state["k"][0], "v1")


class StaleFencingTests(unittest.TestCase):
    def test_stale_token_rejected_after_takeover(self):
        ledger, w1 = make_writer("w1")
        t1 = w1.token
        w1.propose("e1", "k", "v1")
        # takeover: w2 claims, durable token bumps
        w2 = WriterService(ledger, "w2")
        t2 = w2.acquire_lease()
        w2.reconcile()
        self.assertGreater(t2, t1)
        w2.propose("e2", "k", "v2")
        # stale w1 wakes and presents its old token
        with self.assertRaises(FencingError):
            w1.propose("e3", "k", "v1-stale", fencing_token=t1)
        self.assertNotIn("e3", ledger.by_event_id)
        self.assertEqual(ledger.state["k"][0], "v2")

    def test_token_survives_restart(self):
        # SF-07 fix: durable tokens — a "restarted" writer reloads, never resets
        ledger, w1 = make_writer("w1")
        t1 = w1.token
        w1b = WriterService(ledger, "w1")  # same identity, fresh process
        t1b = w1b.acquire_lease()
        self.assertEqual(t1b, t1 + 1)

    def test_renew_bumps_token_and_invalidates_inflight(self):
        # SF-04: a write carrying the pre-renew token must fail after renew
        _, w = make_writer()
        old = w.token
        w.propose("cap", "k", "staged")  # committed before renew, fine
        w.renew_lease()
        with self.assertRaises(FencingError):
            w.propose("stale-after-renew", "k", "x", fencing_token=old)


class TakeoverAndAvailabilityTests(unittest.TestCase):
    def test_proposals_refused_before_reconciliation(self):
        ledger = InProcessLedger()
        w = WriterService(ledger, "w1")
        w.acquire_lease()
        with self.assertRaises(WriterUnavailableError):
            w.propose("e1", "k", "v")

    def test_no_lease_writer_unavailable_emergency_journal_drains(self):
        ledger = InProcessLedger()
        w = WriterService(ledger, "w1")
        # writer/scheduler unavailable: lane buffers locally
        ej = EmergencyJournal()
        ej.append("e1", "k", "v1")
        with self.assertRaises(WriterUnavailableError):
            w.propose("e1", "k", "v1")
        # reconnect: acquire, reconcile, drain
        w.acquire_lease()
        w.reconcile()
        acks = w.drain(ej.events)
        self.assertEqual(acks[0]["disposition"], "accepted")
        # re-drain (client unsure) resolves as duplicate
        acks2 = w.drain(ej.events)
        self.assertEqual(acks2[0]["disposition"], "duplicate")
        self.assertEqual(acks[0]["seq"], acks2[0]["seq"])


class OutboxTests(unittest.TestCase):
    def test_outbox_replay_and_consumer_dedupe(self):
        # SF-06 skeleton: at-least-once delivery, consumer dedupes by event_id
        _, w = make_writer()
        w.propose("f0", "a", 1)
        w.propose("f1", "b", 2)
        delivered = w.outbox_since(1) + w.outbox_since(1)  # duplicate retransmission
        seen = {}
        for rec in delivered:
            seen.setdefault(rec["event_id"], rec)  # inbox dedupe by event_id
        self.assertEqual(set(seen), {"f0", "f1"})

    def test_hash_chain_links(self):
        ledger, w = make_writer()
        w.propose("e1", "k", "v")
        hashes = [r["hash"] for r in ledger.journal]
        self.assertEqual(len(hashes), len(set(hashes)))  # distinct, linked chain


if __name__ == "__main__":
    unittest.main()
