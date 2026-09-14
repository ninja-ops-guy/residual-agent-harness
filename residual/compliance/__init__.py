"""SPEC-ENT-002 Compliance and Audit Framework (stdlib-only, offline).

Implements ENT2-R1 (tagging), ENT2-R2 (retention), ENT2-R3 (legal hold),
ENT2-R4 (data residency), ENT2-R5 (GDPR Art. 17 erasure), ENT2-R6 (reports),
ENT2-R7 (signed report export), and ENT2-R8 (SIEM forwarding).
"""
from .log import ObservationEvent, ObservationLog
from .tagging import ComplianceTagger, TagPolicy
from .retention import ArchiveStore, RetentionPolicy, RetentionReport, enforce_retention
from .legal_hold import HoldScope, LegalHold, LegalHoldManager
from .residency import RegionStore, ResidencyPolicy, TransferApproval
from .erasure import ErasureService, ErasureResult
from .signing import HmacSigner, Signer, SignedReport
from .reports import ReportRequest, ReportType, generate_report, export_csv, export_json, export_pdf
from .siem import CefFormatter, Forwarder, SiemTarget, SpoolQueue, SyslogTransport

__all__ = [
    "ArchiveStore", "CefFormatter", "ComplianceTagger", "ErasureResult",
    "ErasureService", "Forwarder", "HmacSigner", "HoldScope", "LegalHold",
    "LegalHoldManager", "ObservationEvent", "ObservationLog", "RegionStore",
    "ReportRequest", "ReportType", "ResidencyPolicy", "RetentionPolicy",
    "RetentionReport", "SignedReport", "Signer", "SiemTarget", "SpoolQueue",
    "SyslogTransport", "TagPolicy", "TransferApproval", "export_csv",
    "export_json", "export_pdf", "generate_report", "enforce_retention",
]
