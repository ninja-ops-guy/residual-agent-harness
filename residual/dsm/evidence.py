"""Machine-readable evidence generator for SPEC-SWARM-DSM-004 (gate B).

Runs the deterministic fault matrix and the recovery suite, captures raw
event logs, and binds the artifact to the exact git commit/tree identity.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from residual.core import canonical

from .delivery import Inbox, Outbox
from .faults import Fault, FaultSchedule, simulate
from .recovery import run_recovery_suite

EVIDENCE_SCHEMA_VERSION = 1


def _git(repo_root, *args):
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, check=True, timeout=30,
        ).stdout.strip()
    except Exception:
        return None


def source_identity(repo_root):
    return {
        "commit": _git(repo_root, "rev-parse", "HEAD"),
        "tree": _git(repo_root, "rev-parse", "HEAD^{tree}"),
        "branch": _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }


def run_fault_matrix(tmp_root):
    """Duplicate / delayed / reordered / lost delivery, deterministically.

    Convergence claim: with outbox retransmission of unacked messages, the
    accepted event set equals the no-fault case for every schedule.
    """
    tmp_root = Path(tmp_root)
    base_events = [
        {"event_id": f"m{i}", "domain": "receipt.publication", "entity": f"t{i}",
         "value": {"seq": i}, "writer": "verifier"}
        for i in range(6)
    ]
    schedules = {
        "clean": FaultSchedule(),
        "duplicate": FaultSchedule.of(Fault(at=1, kind="duplicate"),
                                      Fault(at=4, kind="duplicate")),
        "delayed": FaultSchedule.of(Fault(at=0, kind="delay", param=2),
                                    Fault(at=3, kind="delay", param=1)),
        "reordered": FaultSchedule.of(Fault(at=1, kind="reorder"),
                                      Fault(at=3, kind="reorder")),
        "lost": FaultSchedule.of(Fault(at=2, kind="loss")),
        "combined": FaultSchedule.of(Fault(at=0, kind="delay", param=2),
                                     Fault(at=1, kind="duplicate"),
                                     Fault(at=3, kind="reorder"),
                                     Fault(at=4, kind="loss")),
    }
    expected_ids = sorted(e["event_id"] for e in base_events)
    cases = []
    for name, schedule in schedules.items():
        case_dir = tmp_root / "faults" / name
        outbox = Outbox(case_dir / "outbox.journal")
        inbox = Inbox(case_dir / "inbox.journal")
        for event in base_events:
            outbox.publish(event)
        # first pass through the faulty channel
        delivered = simulate(outbox.pending(), schedule)
        for event in delivered:
            if inbox.deliver(event) == "accepted":
                outbox.ack(event["event_id"])
        # retransmission pass: whatever was lost is still pending in the
        # durable outbox (no ack), so it is resent on a clean channel.
        retransmitted = list(outbox.pending())
        for event in simulate(retransmitted, FaultSchedule()):
            if inbox.deliver(event) == "accepted":
                outbox.ack(event["event_id"])
        accepted_ids = sorted(
            r["payload"]["event"]["event_id"]
            for r in inbox.journal.replay(-1)
            if r["kind"] == "deliver" and r["payload"]["disposition"] == "accepted")
        trace = [e["event_id"] for e in delivered]
        cases.append({
            "schedule": name,
            "faults": schedule.as_list(),
            "delivery_trace": trace,
            "duplicate_deliveries": len(trace) - len(set(trace)),
            "retransmitted": [e["event_id"] for e in retransmitted],
            "accepted_ids": accepted_ids,
            "converged": accepted_ids == expected_ids,
            "idempotent": len(accepted_ids) == len(set(accepted_ids)),
        })
    return {
        "matrix": cases,
        "all_converged": all(c["converged"] for c in cases),
        "all_idempotent": all(c["idempotent"] for c in cases),
        "ok": all(c["converged"] and c["idempotent"] for c in cases),
    }


def generate_evidence(output_dir, repo_root):
    """Write evidence/dsm/dsm-004-evidence.json; return (path, sha256)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dsm-evidence-") as tmp:
        fault_matrix = run_fault_matrix(tmp)
        recovery = run_recovery_suite(Path(tmp) / "recovery", keep=True)
        raw_logs = {}
        for journal in sorted(Path(tmp).rglob("*.journal*")):
            if journal.is_file():
                raw_logs[str(journal.relative_to(tmp))] = \
                    journal.read_text(encoding="utf-8").splitlines()
    artifact = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "spec": "SPEC-SWARM-DSM-004",
        "source_identity": source_identity(repo_root),
        "fault_matrix": fault_matrix,
        "recovery_suite": recovery,
        "raw_event_logs": raw_logs,
        "results": {
            "no_duplicate_accepted_transition":
                recovery["no_duplicate_accepted_transition"],
            "fault_matrix_ok": fault_matrix["ok"],
            "ok": fault_matrix["ok"] and recovery["ok"],
        },
    }
    text = canonical(artifact) + "\n"
    path = output_dir / "dsm-004-evidence.json"
    path.write_text(text, encoding="utf-8")
    return path, hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    import os
    repo = Path(__file__).resolve().parents[2]
    out = repo / "evidence" / "dsm"
    p, h = generate_evidence(out, repo)
    print(json.dumps({"artifact": str(p), "sha256": h}, indent=2))
