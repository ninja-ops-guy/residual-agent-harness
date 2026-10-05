"""CLI for the deterministic RESIDUAL acceleration control plane."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from residual.control_plane.acceleration import AccelerationConductor, PortfolioManifest
from residual.core import ContractError, strict_json


def _load(path: str) -> AccelerationConductor:
    raw = strict_json(Path(path).read_text(encoding="utf-8"))
    return AccelerationConductor(PortfolioManifest.from_dict(raw))


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="residual ops",
        description="Derive release/research readiness without crossing authority gates",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "owner-queue", "ready", "validate"):
        cmd = sub.add_parser(name)
        cmd.add_argument("manifest", help="Acceleration control-plane JSON manifest")

    args = parser.parse_args(argv)
    try:
        conductor = _load(args.manifest)
        if args.command == "status":
            _print(conductor.snapshot())
        elif args.command == "owner-queue":
            _print({
                "manifest_hash": conductor.manifest.manifest_hash,
                "owner_queue": conductor.owner_queue(),
            })
        elif args.command == "ready":
            _print({
                "manifest_hash": conductor.manifest.manifest_hash,
                "ready_work": conductor.ready_work(),
            })
        else:
            _print({
                "schema_version": conductor.manifest.to_dict()["schema_version"],
                "manifest_hash": conductor.manifest.manifest_hash,
                "lane_count": len(conductor.manifest.lanes),
                "task_count": len(conductor.manifest.tasks),
                "release_freeze": conductor.manifest.release_freeze,
            })
        return 0
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"residual ops: {type(exc).__name__}: manifest could not be validated", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
