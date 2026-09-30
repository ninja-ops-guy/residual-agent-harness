"""Operator CLI for execution-substrate qualification artifacts.

This surface only verifies and inspects previously generated evidence. It never
creates a PASS record from command-line assertions and never grants execution
authority.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ..core import ContractError
from .ledger import SubstrateQualificationLedger

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _load(path: str) -> SubstrateQualificationLedger:
    return SubstrateQualificationLedger.load(Path(path))


def _emit(payload: dict, *, as_json: bool, human: str) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(human)
    return 0


def cmd_verify(args) -> int:
    ledger = _load(args.ledger)
    actual = ledger.ledger_digest
    if args.expected_digest is not None:
        if not _HEX64.fullmatch(args.expected_digest):
            raise ContractError("expected ledger digest must be lowercase sha256")
        if actual != args.expected_digest:
            raise ContractError("qualification ledger digest does not match expected digest")
    records = ledger.records
    payload = {
        "schema_version": ledger.schema_version,
        "status": "VALID",
        "ledger_digest": actual,
        "records": len(records),
        "pass_records": sum(record.overall == "PASS" for record in records),
        "non_pass_records": sum(record.overall != "PASS" for record in records),
    }
    return _emit(
        payload,
        as_json=args.json,
        human=(
            f"qualification ledger VALID: {actual} "
            f"({payload['records']} record(s), {payload['pass_records']} PASS)"
        ),
    )


def cmd_status(args) -> int:
    ledger = _load(args.ledger)
    rows = []
    for record in ledger.records:
        tuple_digest = record.qualification_tuple.tuple_digest
        if args.tuple_digest and tuple_digest != args.tuple_digest:
            continue
        rows.append({
            "tuple_digest": tuple_digest,
            "record_digest": record.record_digest,
            "substrate": record.qualification_tuple.substrate_name,
            "version": record.qualification_tuple.substrate_version,
            "driver": record.qualification_tuple.driver,
            "platform_class": record.qualification_tuple.platform_class,
            "agent_profile": record.qualification_tuple.agent_profile,
            "overall": record.overall,
            "qualified_capabilities": sorted(record.qualified_capabilities),
            "limitations": sorted(record.limitations),
        })
    if args.tuple_digest and not rows:
        raise ContractError("tuple digest is not present in qualification ledger")
    payload = {
        "ledger_digest": ledger.ledger_digest,
        "records": rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"qualification ledger {ledger.ledger_digest}")
    for row in rows:
        caps = ",".join(row["qualified_capabilities"]) or "(none)"
        print(
            f"{row['substrate']}@{row['version']} "
            f"{row['driver']}/{row['platform_class']} "
            f"{row['agent_profile']} {row['overall']} caps={caps} "
            f"tuple={row['tuple_digest']} record={row['record_digest']}"
        )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="residual substrate",
        description="Verify and inspect execution-substrate qualification evidence",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser(
        "verify-ledger",
        help="Strictly validate a content-addressed substrate qualification ledger",
    )
    verify.add_argument("ledger")
    verify.add_argument("--expected-digest")
    verify.add_argument("--json", action="store_true")

    status = sub.add_parser(
        "status",
        help="Show qualification records and evidence-backed capabilities",
    )
    status.add_argument("ledger")
    status.add_argument("--tuple-digest")
    status.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "verify-ledger":
            return cmd_verify(args)
        return cmd_status(args)
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        print(
            f"residual substrate: {type(exc).__name__}: "
            "qualification evidence could not be validated",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
