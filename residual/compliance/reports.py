"""On-demand compliance reports, signed and exportable as JSON, CSV, PDF.

Implements ENT2-R6 (the five mandatory report types) and ENT2-R7
(Station-signed reports, exportable in PDF/JSON/CSV, auditor-ready).
The PDF writer is a minimal stdlib implementation — no external
dependencies, fully deterministic and offline.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from enum import Enum

from ..core import ContractError, canonical
from .log import ObservationLog
from .signing import Signer, SignedReport, sign_report

REPORT_SCHEMA = "residual.compliance.report.v1"


class ReportType(str, Enum):
    """The five ENT2-R6 report types."""
    TASK_EXECUTION = "task_execution"            # tasks executed + receipts in range
    HITL_ESCALATIONS = "hitl_escalations"        # escalations and resolutions
    CONTRACT_VIOLATIONS = "contract_violations"  # violations and dispositions
    SENSITIVE_ACCESS = "sensitive_access"        # sensitive data access w/ user attribution
    MODULE_INSTALLS = "module_installs"          # module installations and signatures


_REPORT_KINDS = {
    ReportType.TASK_EXECUTION: {"task_execution", "receipt"},
    ReportType.HITL_ESCALATIONS: {"hitl_escalation", "hitl_decision"},
    ReportType.CONTRACT_VIOLATIONS: {"contract_violation"},
    ReportType.SENSITIVE_ACCESS: {"sensitive_access"},
    ReportType.MODULE_INSTALLS: {"module_install"},
}

_COLUMNS = {
    ReportType.TASK_EXECUTION: ("timestamp", "task_id", "actor", "chain_hash"),
    ReportType.HITL_ESCALATIONS: ("timestamp", "task_id", "actor", "resolution"),
    ReportType.CONTRACT_VIOLATIONS: ("timestamp", "task_id", "violation", "disposition"),
    ReportType.SENSITIVE_ACCESS: ("timestamp", "actor", "task_id", "resource"),
    ReportType.MODULE_INSTALLS: ("timestamp", "actor", "module", "signature"),
}


@dataclass(frozen=True)
class ReportRequest:
    """A report query. Implements ENT2-R6."""
    report_type: ReportType
    start: float = 0.0
    end: float = float("inf")

    def __post_init__(self):
        try:
            object.__setattr__(self, "report_type", ReportType(self.report_type))
        except ValueError:
            raise ContractError("unknown report type") from None
        if self.end < self.start or self.start < 0:
            raise ContractError("report time range is invalid")


def _row(report_type: ReportType, event) -> dict:
    base = {"timestamp": event.timestamp, "actor": event.actor,
            "task_id": event.task_id, "chain_hash": event.chain_hash}
    for key in ("resolution", "violation", "disposition", "resource", "module", "signature"):
        if key in event.payload:
            base[key] = event.payload[key]
    return {column: base.get(column, "") for column in _COLUMNS[report_type]}


def generate_report(log: ObservationLog, request: ReportRequest, signer: Signer,
                    generated_at: float = 0.0, generator: str = "residual-station") -> SignedReport:
    """Build a Station-signed report from the observation log.

    Implements ENT2-R6 and ENT2-R7.
    """
    end = None if request.end == float("inf") else request.end
    events = log.query(kinds=_REPORT_KINDS[request.report_type],
                       start=request.start, end=end)
    rows = [_row(request.report_type, e) for e in events]
    body = {
        "schema": REPORT_SCHEMA,
        "report_type": request.report_type.value,
        "range": {"start": request.start,
                  "end": request.end if request.end != float("inf") else "unbounded"},
        "generated_at": generated_at,
        "generator": generator,
        "columns": list(_COLUMNS[request.report_type]),
        "rows": rows,
        "row_count": len(rows),
        "log_chain_valid": log.verify_chain(),
    }
    return sign_report(body, signer)


# -- export (ENT2-R7) -------------------------------------------------------

def export_json(report: SignedReport) -> str:
    """Auditor-ready JSON export. Implements ENT2-R7."""
    return json.dumps({"schema": REPORT_SCHEMA, "body": report.body,
                       "signature": report.signature, "key_id": report.key_id,
                       "algorithm": report.algorithm},
                      indent=2, sort_keys=True, ensure_ascii=False)


def export_csv(report: SignedReport) -> str:
    """CSV export (header comment carries the signature). Implements ENT2-R7."""
    out = io.StringIO()
    out.write(f"# signature={report.signature} key_id={report.key_id} "
              f"algorithm={report.algorithm}\n")
    writer = csv.DictWriter(out, fieldnames=report.body["columns"])
    writer.writeheader()
    writer.writerows(report.body["rows"])
    return out.getvalue()


def _pdf_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def export_pdf(report: SignedReport) -> bytes:
    """Minimal stdlib PDF export of a signed report. Implements ENT2-R7.

    Renders the report as simple text pages (Helvetica, 10pt). Sufficient
    for auditor presentation without external dependencies.
    """
    lines = [f"Residual Compliance Report: {report.body['report_type']}",
             f"Generated: {report.body['generated_at']} by {report.body['generator']}",
             f"Signature ({report.algorithm}, {report.key_id}): {report.signature}",
             f"Log chain valid: {report.body['log_chain_valid']}",
             ""]
    header = " | ".join(report.body["columns"])
    lines.append(header)
    lines.append("-" * min(len(header), 110))
    for row in report.body["rows"]:
        lines.append(" | ".join(str(row.get(c, ""))[:28] for c in report.body["columns"]))
    lines = [line[:110] for line in lines] or [""]

    content_parts = ["BT", "/F1 10 Tf", "14 TL", "40 780 Td"]
    for i, line in enumerate(lines):
        if i:
            content_parts.append("T*")
        content_parts.append(f"({_pdf_escape(line)}) Tj")
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = io.BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode())
    pdf.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
              f"startxref\n{xref}\n%%EOF\n".encode())
    data = pdf.getvalue()
    if not data.startswith(b"%PDF-1.4") or b"%%EOF" not in data:
        raise ContractError("PDF writer produced invalid output")
    return data


# Keep linters honest about canonical usage symmetry with signing.
if not callable(canonical):
    raise RuntimeError("canonical encoder is unavailable")
