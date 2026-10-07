"""Tests for SPEC-ENT-002 (Compliance and Audit Framework), ENT2-R1..R8."""
import json

import pytest

from residual.core import ContractError
from residual.compliance import (
    ArchiveStore, CefFormatter, ComplianceTagger, ErasureService, Forwarder,
    HmacSigner, HoldScope, LegalHoldManager, ObservationLog, RegionStore,
    ReportRequest, ReportType, ResidencyPolicy, RetentionPolicy, SpoolQueue,
    TagPolicy, enforce_retention, export_csv, export_json, export_pdf,
    generate_report,
)
from residual.compliance.retention import SECONDS_PER_YEAR, enforce_retention as _er

YEAR = SECONDS_PER_YEAR


@pytest.fixture
def log():
    return ObservationLog()


@pytest.fixture
def populated(log):
    log.append("task_execution", 10, "alice", "t1", category="sox", region="local",
               payload={"module": "m1", "signature": "sig"})
    log.append("hitl_escalation", 20, "bob", "t1", payload={"resolution": "approved"})
    log.append("contract_violation", 30, "alice", "t2",
               payload={"violation": "v1", "disposition": "quarantined"})
    log.append("sensitive_access", 40, "carol", "t2", payload={"resource": "db/customers"})
    log.append("module_install", 50, "dave", "t3",
               payload={"module": "m2", "signature": "abc123"})
    return log


# ENT2-R1 -----------------------------------------------------------------

class TestTagging:
    def test_default_policy_tags(self, log):
        event = log.append("receipt", 1, "alice", "t1")
        tagged = ComplianceTagger().tag(event)
        assert "SOX-CC7.2" in tagged.tags and "GDPR-Art32" in tagged.tags

    def test_custom_policy_per_deployment(self, log):
        policy = TagPolicy({"receipt": ("HIPAA-164.312",)})
        tagged = ComplianceTagger(policy).tag(log.append("receipt", 1, "a", "t"))
        assert tagged.tags == ("HIPAA-164.312",)

    def test_invalid_tag_rejected(self, log):
        with pytest.raises(ContractError):
            ComplianceTagger().tag(log.append("receipt", 1, "a", "t"), extra=("bad tag",))

    def test_chain_integrity(self, populated):
        assert populated.verify_chain()
        tampered = populated._events[2]
        populated._events[2] = type(tampered)(
            **{**tampered.__dict__, "actor": "mallory"})
        assert not populated.verify_chain()


# ENT2-R2 -----------------------------------------------------------------

class TestRetention:
    def test_defaults(self):
        policy = RetentionPolicy()
        assert policy.max_age_seconds("sox") == 7 * YEAR
        assert policy.max_age_seconds("operational") == 3 * YEAR
        assert policy.max_age_seconds("debug") == YEAR

    def test_archive_before_delete(self, log):
        log.append("observation", 0, "a", "t", category="debug")
        log.append("observation", 8 * YEAR, "a", "t", category="sox")
        archive = ArchiveStore()
        report = enforce_retention(log, archive, RetentionPolicy(), now=2 * YEAR)
        assert report.deleted == (1,) and report.archived == (1,)
        assert archive.records[0].event.id == 1
        assert [e.id for e in log.events] == [2, 3]  # 3 = retention receipt

    def test_policy_validation(self):
        with pytest.raises(ContractError):
            RetentionPolicy({"sox": 7, "operational": 3})  # missing debug
        with pytest.raises(ContractError):
            RetentionPolicy({"sox": 0, "operational": 3, "debug": 1})


# ENT2-R3 -----------------------------------------------------------------

class TestLegalHold:
    def test_hold_blocks_delete_and_release_allows(self, log):
        old = log.append("observation", 0, "alice", "t1", category="debug")
        holds = LegalHoldManager(log)
        hold = holds.activate(HoldScope(user="alice"), "litigation", timestamp=1)
        archive = ArchiveStore()
        report = enforce_retention(log, archive, RetentionPolicy(), now=2 * YEAR, holds=holds)
        assert old.id in report.held and not archive.records
        assert holds.blocked(old)
        holds.release(hold.id, timestamp=2)
        assert not holds.blocked(old)
        report = enforce_retention(log, archive, RetentionPolicy(), now=2 * YEAR, holds=holds)
        assert old.id in report.deleted

    def test_scopes(self, log):
        holds = LegalHoldManager(log)
        e1 = log.append("observation", 5, "alice", "t1")
        e2 = log.append("observation", 50, "alice", "t2")
        e3 = log.append("observation", 5, "bob", "t1")
        holds.activate(HoldScope(user="alice", start=0, end=10), "audit", timestamp=6)
        assert holds.blocked(e1) and not holds.blocked(e2) and not holds.blocked(e3)

    def test_hold_actions_receipted(self, log):
        holds = LegalHoldManager(log)
        hold = holds.activate(HoldScope(user="alice"), "r", timestamp=1)
        holds.release(hold.id, timestamp=2)
        events = log.query(kinds={"legal_hold"})
        assert [e.payload["action"] for e in events] == ["activate", "release"]
        assert all(e.chain_hash for e in events)
        with pytest.raises(ContractError):
            holds.release(hold.id, timestamp=3)

    def test_empty_scope_rejected(self):
        with pytest.raises(ContractError):
            HoldScope()


# ENT2-R4 -----------------------------------------------------------------

class TestResidency:
    def test_store_in_execution_region(self, log, tmp_path):
        policy = ResidencyPolicy(regions=("local", "eu-west-1", "us-east-1"))
        store = RegionStore(tmp_path, policy, log)
        event = log.append("receipt", 1, "a", "t", region="eu-west-1")
        path = store.store(event)
        assert path.parent.name == "eu-west-1" and path.exists()

    def test_cross_border_requires_approval(self, log, tmp_path):
        policy = ResidencyPolicy(regions=("eu-west-1", "us-east-1"),
                                 allowed_flows=(("eu-west-1", "us-east-1"),))
        store = RegionStore(tmp_path, policy, log)
        event = log.append("receipt", 1, "a", "t", region="eu-west-1")
        with pytest.raises(ContractError):
            store.transfer(event, "us-east-1", approved=False)

    def test_unpermitted_flow_rejected_even_with_approval(self, log, tmp_path):
        policy = ResidencyPolicy(regions=("eu-west-1", "us-east-1"))
        store = RegionStore(tmp_path, policy, log)
        event = log.append("receipt", 1, "a", "t", region="eu-west-1")
        with pytest.raises(ContractError):
            store.transfer(event, "us-east-1", approved=True, approver="ciso")

    def test_approved_transfer_observed(self, log, tmp_path):
        policy = ResidencyPolicy(regions=("eu-west-1", "us-east-1"),
                                 allowed_flows=(("eu-west-1", "us-east-1"),))
        store = RegionStore(tmp_path, policy, log)
        event = log.append("receipt", 1, "a", "t", region="eu-west-1")
        path = store.transfer(event, "us-east-1", approved=True, approver="ciso", timestamp=2)
        assert path.parent.name == "us-east-1"
        transfers = log.query(kinds={"transfer"})
        assert len(transfers) == 1
        assert transfers[0].payload["approver"] == "ciso"
        assert store.approvals[0].receipt_hash == transfers[0].chain_hash


# ENT2-R5 -----------------------------------------------------------------

class TestErasure:
    def test_pseudonymization(self, populated):
        service = ErasureService(populated)
        before = len(populated.events)
        result = service.pseudonymize("alice", timestamp=100)
        assert result.events_pseudonymized == 2
        assert result.salt_destroyed
        assert len(populated.events) == before + 1  # receipts preserved + erasure receipt
        actors = {e.actor for e in populated.events}
        assert "alice" not in actors and result.pseudonym in actors
        assert all(e.payload.get("pseudonymized") for e in populated.events
                   if e.actor == result.pseudonym)
        assert populated.verify_chain()
        assert populated.query(kinds={"erasure"})[-1].chain_hash == result.receipt_hash

    def test_double_erasure_rejected(self, populated):
        service = ErasureService(populated)
        service.pseudonymize("alice", timestamp=100)
        with pytest.raises(ContractError):
            service.pseudonymize("alice", timestamp=101)

    def test_irreversible_hash(self, populated):
        # Two services produce different pseudonyms (random salt, destroyed).
        r1 = ErasureService(populated).pseudonymize("alice", timestamp=100)
        log2 = ObservationLog()
        log2.append("receipt", 1, "alice", "t")
        r2 = ErasureService(log2).pseudonymize("alice", timestamp=100)
        assert r1.pseudonym != r2.pseudonym


# ENT2-R6 / ENT2-R7 ---------------------------------------------------------

class TestReports:
    KEY = b"station-test-key-0123456789"

    def test_all_five_report_types(self, populated):
        signer = HmacSigner(self.KEY)
        expected = {
            ReportType.TASK_EXECUTION: 1, ReportType.HITL_ESCALATIONS: 1,
            ReportType.CONTRACT_VIOLATIONS: 1, ReportType.SENSITIVE_ACCESS: 1,
            ReportType.MODULE_INSTALLS: 1,
        }
        for report_type, count in expected.items():
            report = generate_report(populated, ReportRequest(report_type), signer,
                                     generated_at=60)
            assert report.body["row_count"] == count
            assert report.body["log_chain_valid"] is True

    def test_time_range_filter(self, populated):
        report = generate_report(populated, ReportRequest(ReportType.TASK_EXECUTION, 15, 60),
                                 HmacSigner(self.KEY))
        assert report.body["row_count"] == 0
        report = generate_report(populated, ReportRequest(ReportType.TASK_EXECUTION, 0, 10),
                                 HmacSigner(self.KEY))
        assert report.body["row_count"] == 1

    def test_signature_verifies_and_tamper_fails(self, populated):
        signer = HmacSigner(self.KEY)
        report = generate_report(populated, ReportRequest(ReportType.SENSITIVE_ACCESS), signer)
        assert report.verify(signer)
        body = dict(report.body, row_count=999)
        assert not type(report)(body, report.signature, report.key_id).verify(signer)
        other = HmacSigner(b"other-station-key-0123456")
        assert not report.verify(other)

    def test_json_and_csv_exports(self, populated):
        report = generate_report(populated, ReportRequest(ReportType.MODULE_INSTALLS),
                                 HmacSigner(self.KEY), generated_at=60)
        data = json.loads(export_json(report))
        assert data["signature"] == report.signature
        assert data["body"]["rows"][0]["module"] == "m2"
        csv_text = export_csv(report)
        assert csv_text.splitlines()[0].startswith("# signature=")
        assert "module,signature" in csv_text and "m2,abc123" in csv_text

    def test_pdf_export(self, populated):
        report = generate_report(populated, ReportRequest(ReportType.CONTRACT_VIOLATIONS),
                                 HmacSigner(self.KEY))
        pdf = export_pdf(report)
        assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
        assert b"quarantined" in pdf and report.signature.encode() in pdf

    def test_pluggable_signer(self, populated):
        class NullSigner:
            key_id = "null"

            def sign(self, message):
                return "deadbeef" * 8

        report = generate_report(populated, ReportRequest(ReportType.HITL_ESCALATIONS),
                                 NullSigner())
        assert report.key_id == "null" and report.verify(NullSigner())


# ENT2-R8 -----------------------------------------------------------------

class FakeTransport:
    def __init__(self, fail_times=0):
        self.sent = []
        self.fail_times = fail_times

    def send(self, message):
        if self.fail_times:
            self.fail_times -= 1
            raise OSError("simulated outage")
        self.sent.append(message)


class TestSiem:
    def _setup(self, tmp_path, fail_times=0):
        log = ObservationLog()
        spool = SpoolQueue(tmp_path / "spool.jsonl")
        transport = FakeTransport(fail_times)
        fwd = Forwarder("splunk", transport, spool, log, sleep=lambda _: None)
        return log, spool, transport, fwd

    def test_cef_format(self, log):
        event = log.append("contract_violation", 1, "ali|ce", "t1")
        line = CefFormatter().format(event)
        assert line.startswith("CEF:0|Residual|Station|1.0|contract_violation|")
        assert "|8|" in line and "suser=ali\\|ce" in line
        assert f"cs3={event.chain_hash}" in line

    def test_real_time_forward_and_observed(self, tmp_path):
        log, spool, transport, fwd = self._setup(tmp_path)
        event = log.append("observation", 1, "a", "t")
        assert fwd.forward(event, timestamp=2)
        assert len(transport.sent) == 1 and len(spool) == 0
        siem_events = log.query(kinds={"siem"})
        assert siem_events and siem_events[0].payload["target"] == "splunk"

    def test_at_least_once_with_retry_and_durable_spool(self, tmp_path):
        log, spool, transport, fwd = self._setup(tmp_path, fail_times=4)
        event = log.append("observation", 1, "a", "t")
        assert not fwd.forward(event)  # outage; stays spooled
        assert len(spool) == 1
        # Durable: a new queue over the same file sees the record.
        assert len(SpoolQueue(tmp_path / "spool.jsonl")) == 1
        assert fwd.flush(max_attempts=5)
        assert len(spool) == 0
        assert transport.sent.count(spool.pending() or transport.sent[0]) >= 1
        assert len(transport.sent) == 1  # exactly once delivered, >=1 attempted
        assert transport.sent[0].count("CEF:0") == 1

    def test_all_targets(self, tmp_path):
        for i, target in enumerate(("splunk", "sentinel", "qradar")):
            log = ObservationLog()
            fwd = Forwarder(target, FakeTransport(),
                            SpoolQueue(tmp_path / f"s{i}.jsonl"), sleep=lambda _: None)
            assert fwd.forward(log.append("observation", 1, "a", "t"))

    def test_unknown_target_rejected(self, tmp_path):
        with pytest.raises(ContractError):
            Forwarder("datadog", FakeTransport(), SpoolQueue(tmp_path / "x.jsonl"))


def test_requirement_ids_in_docstrings():
    import inspect
    import residual.compliance as pkg
    import residual.compliance.log as log_mod

    modules = [pkg, log_mod]
    for name in ("tagging", "retention", "legal_hold", "residency", "erasure",
                 "reports", "signing", "siem"):
        modules.append(__import__(f"residual.compliance.{name}", fromlist=["x"]))
    for module in modules:
        assert "ENT2-R" in (module.__doc__ or "")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module.__name__ and not obj.__name__.startswith("_"):
                assert "ENT2-R" in (obj.__doc__ or ""), obj.__name__
