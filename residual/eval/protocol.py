"""Offline integrity/readiness checks; this module never invokes a provider."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .workload import FrozenWorkload


class ProtocolError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protocol(path: Path, root: Path, *, expected_sha256: str,
                      require_frozen: bool = False) -> dict:
    """Validate a byte commitment and bundled workload, returning the protocol.

    A self-declared ready/frozen flag is never permission for live execution.
    This version only qualifies preparation artifacts; no R0-R5 adapter exists.
    """
    if file_sha256(path) != expected_sha256:
        raise ProtocolError("protocol SHA256 mismatch")
    protocol = json.loads(path.read_text())
    if protocol.get("schema_version") != "residual.r0-r5.protocol.v1":
        raise ProtocolError("unsupported protocol schema")
    if [c["id"] for c in protocol["configurations"]] != [f"R{i}" for i in range(6)]:
        raise ProtocolError("R0-R5 must appear exactly once in order")
    workload_ref = protocol["workload"]
    relative = Path(workload_ref["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ProtocolError("workload path must be repository-relative")
    workload_path = (root / relative).resolve()
    if not workload_path.is_relative_to(root.resolve()):
        raise ProtocolError("workload path escapes repository")
    if file_sha256(workload_path) != workload_ref["sha256"]:
        raise ProtocolError("workload SHA256 mismatch")
    workload = FrozenWorkload.from_json(workload_path.read_text())
    if workload.manifest_hash != workload_ref["manifest_hash"]:
        raise ProtocolError("workload manifest mismatch")
    if [t.task_id for t in workload.tasks] != protocol["task_population"]:
        raise ProtocolError("task population mismatch")
    if type(protocol["repetitions"]) is not int or protocol["repetitions"] < 3:
        raise ProtocolError("at least three repetitions required")
    seeds = protocol["seeds"]
    if len(seeds) != protocol["repetitions"] or any(type(s) is not int for s in seeds):
        raise ProtocolError("one integer schedule seed required per repetition")
    if protocol.get("frozen") is not False or protocol.get("live_execution_enabled") is not False:
        raise ProtocolError("v1 preparation checker cannot qualify live execution")
    if protocol.get("readiness") != "blocked" or not protocol.get("blockers"):
        raise ProtocolError("preparation must preserve explicit readiness blockers")
    if require_frozen:
        raise ProtocolError("confirmatory freeze unavailable: " + "; ".join(protocol["blockers"]))
    return protocol


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--require-frozen", action="store_true")
    args = parser.parse_args()
    try:
        p = validate_protocol(args.protocol, args.root, expected_sha256=args.protocol_sha256,
                              require_frozen=args.require_frozen)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"protocol rejected: {exc}\n")
    print(json.dumps({"integrity": "PASS", "readiness": p["readiness"], "blockers": p["blockers"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
