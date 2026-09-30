"""Operator CLI for execution-substrate qualification artifacts.

This surface only verifies and inspects previously generated evidence. It never
creates a PASS record from command-line assertions and never grants execution
authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from ..core import ContractError
from .admission import QualificationAdmissionBundle
from .authority_lifecycle import (
    QualificationAuthorityLifecycleBundle,
    QualificationAuthorityPolicy,
    build_lifecycle_admitted_registry,
)
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


def _trusted_keys(values) -> tuple[bytes, ...]:
    keys = []
    for value in values or ():
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ContractError("Station public key must be 32-byte hex")
        keys.append(bytes.fromhex(value))
    if not keys:
        raise ContractError("at least one trusted Station public key is required")
    return tuple(keys)


def cmd_verify_lifecycle(args) -> int:
    ledger = _load(args.ledger)
    admissions = QualificationAdmissionBundle.load(args.admissions)
    lifecycle = QualificationAuthorityLifecycleBundle.load(args.lifecycle)

    for actual, expected, label in (
        (ledger.ledger_digest, args.expected_ledger_digest, "ledger"),
        (admissions.bundle_digest, args.expected_admission_digest, "admission"),
        (lifecycle.bundle_digest, args.expected_lifecycle_digest, "lifecycle"),
    ):
        if expected is not None:
            if not _HEX64.fullmatch(expected):
                raise ContractError(f"expected {label} digest must be lowercase sha256")
            if actual != expected:
                raise ContractError(f"{label} digest does not match expected digest")

    now_ns = time.time_ns() if args.at_ns is None else args.at_ns
    if type(now_ns) is not int or now_ns <= 0:
        raise ContractError("authority evaluation time must be positive")

    roots = _trusted_keys(args.station_public_key_hex)
    admitted = build_lifecycle_admitted_registry(
        ledger.registry(),
        admissions,
        lifecycle,
        root_public_keys=roots,
        policy=QualificationAuthorityPolicy(
            now_ns=now_ns,
            max_admission_age_ns=args.max_admission_age_seconds * 1_000_000_000,
            max_future_skew_ns=args.max_future_skew_seconds * 1_000_000_000,
            min_issued_at_ns=args.min_issued_at_ns,
        ),
        distrusted_key_ids=tuple(args.distrust_key_id or ()),
    )
    snapshot = admitted.snapshot()
    admitted_rows = [row for row in snapshot if row["station_admitted"]]
    payload = {
        "status": "AUTHORITY_LIFECYCLE_VALID",
        "evaluated_at_ns": now_ns,
        "ledger_digest": ledger.ledger_digest,
        "admission_bundle_digest": admissions.bundle_digest,
        "lifecycle_bundle_digest": lifecycle.bundle_digest,
        "admitted_records": admitted_rows,
        "admitted_record_count": len(admitted_rows),
    }
    return _emit(
        payload,
        as_json=args.json,
        human=(
            f"qualification authority lifecycle VALID: {len(admitted_rows)} "
            f"effective record(s) at {now_ns}"
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


def cmd_verify_authority(args) -> int:
    ledger = _load(args.ledger)
    admissions = QualificationAdmissionBundle.load(args.admissions)

    if args.expected_ledger_digest is not None:
        if not _HEX64.fullmatch(args.expected_ledger_digest):
            raise ContractError("expected ledger digest must be lowercase sha256")
        if ledger.ledger_digest != args.expected_ledger_digest:
            raise ContractError("qualification ledger digest does not match expected digest")
    if args.expected_admission_digest is not None:
        if not _HEX64.fullmatch(args.expected_admission_digest):
            raise ContractError("expected admission digest must be lowercase sha256")
        if admissions.bundle_digest != args.expected_admission_digest:
            raise ContractError("qualification admission digest does not match expected digest")

    trusted: dict[str, bytes] = {}
    for value in args.station_public_key_hex or ():
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ContractError("Station public key must be 32-byte hex")
        raw = bytes.fromhex(value)
        trusted[hashlib.sha256(raw).hexdigest()] = raw
    if not trusted:
        raise ContractError("at least one trusted Station public key is required")

    admitted = admissions.admitted_registry(
        ledger.registry(),
        trusted_public_keys=trusted,
    )
    snapshot = admitted.snapshot()
    admitted_rows = [row for row in snapshot if row["station_admitted"]]
    payload = {
        "status": "AUTHORIZED",
        "ledger_digest": ledger.ledger_digest,
        "admission_bundle_digest": admissions.bundle_digest,
        "trusted_station_keys": sorted(trusted),
        "admitted_records": admitted_rows,
    }
    return _emit(
        payload,
        as_json=args.json,
        human=(
            f"qualification authority VALID: {len(admitted_rows)} admitted record(s), "
            f"ledger={ledger.ledger_digest}, admissions={admissions.bundle_digest}"
        ),
    )


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

    authority = sub.add_parser(
        "verify-authority",
        help="Verify Station admissions against pinned trusted public keys",
    )
    authority.add_argument("ledger")
    authority.add_argument("admissions")
    authority.add_argument(
        "--station-public-key-hex",
        action="append",
        required=True,
        help="Trusted raw Ed25519 public key as 64 hex characters (repeatable)",
    )
    authority.add_argument("--expected-ledger-digest")
    authority.add_argument("--expected-admission-digest")
    authority.add_argument("--json", action="store_true")

    lifecycle = sub.add_parser(
        "verify-authority-lifecycle",
        help="Apply Station key rotation, revocation, and admission freshness",
    )
    lifecycle.add_argument("ledger")
    lifecycle.add_argument("admissions")
    lifecycle.add_argument("lifecycle")
    lifecycle.add_argument(
        "--station-public-key-hex",
        action="append",
        required=True,
        help="Pinned root Ed25519 public key as 64 hex characters (repeatable)",
    )
    lifecycle.add_argument(
        "--max-admission-age-seconds",
        type=int,
        required=True,
    )
    lifecycle.add_argument("--max-future-skew-seconds", type=int, default=0)
    lifecycle.add_argument("--min-issued-at-ns", type=int, default=0)
    lifecycle.add_argument("--at-ns", type=int)
    lifecycle.add_argument("--distrust-key-id", action="append")
    lifecycle.add_argument("--expected-ledger-digest")
    lifecycle.add_argument("--expected-admission-digest")
    lifecycle.add_argument("--expected-lifecycle-digest")
    lifecycle.add_argument("--json", action="store_true")

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
        if args.command == "verify-authority":
            return cmd_verify_authority(args)
        if args.command == "verify-authority-lifecycle":
            return cmd_verify_lifecycle(args)
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
