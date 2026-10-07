"""Track G (N9-R19..R22): CLI for `residual node join|leave` and
`residual cluster status`. All commands support machine-readable
``--json`` output.

Cluster membership is persisted to a JSON state file (default
``~/.residual/cluster.json``) so separate CLI invocations share a view
of the cluster. Authentication uses the shared cluster key (HMAC), as in
the in-process protocol.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

from .capabilities import Capability, NodeRecord
from .registry import NodeRegistry
from .schema import ClusterError, supported_versions
from .auth import sign_message, verify_message
from .schema import MessageKind, WireMessage

DEFAULT_STATE = "~/.residual/cluster.json"


def _state_path(args) -> "Path":
    from pathlib import Path
    return Path(args.state_file or DEFAULT_STATE).expanduser()


def _load_registry(path) -> NodeRegistry:
    registry = NodeRegistry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return registry
    for rec in data.get("nodes", []):
        try:
            registry.upsert(NodeRecord.from_dict(rec))
        except (KeyError, ValueError, TypeError):
            continue
    return registry


def _save_registry(path, registry: NodeRegistry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"nodes": [n.to_dict() for n in registry.nodes(
        states=("active", "leaving", "failed"))]}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _capability_from_args(args) -> Capability:
    return Capability(
        models=tuple(args.model or ()),
        tokens_per_second=args.tokens_per_second,
        context_window=args.context_window,
        memory_bytes=args.memory_bytes,
        gpus=args.gpus,
        workers=args.workers,
    )


def _check_key(cluster_key: str, node_id: str) -> None:
    """Authenticate the operation with the cluster key (HMAC round-trip)."""
    msg = sign_message(cluster_key, WireMessage(
        kind=MessageKind.JOIN, sender_id=node_id,
        payload={"ts": time.time_ns()}))
    verify_message(cluster_key, msg)


def _emit(args, payload: dict, human: str) -> int:
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(human)
    return 0


def cmd_join(args) -> int:
    """N9-R19: authenticate with the cluster key, announce capabilities."""
    node_id = args.node_id or f"node-{uuid.uuid4().hex[:12]}"
    _check_key(args.cluster_key, node_id)
    path = _state_path(args)
    registry = _load_registry(path)
    registry.upsert(NodeRecord(
        node_id=node_id, address=args.address or f"local://{node_id}",
        capability=_capability_from_args(args), is_local=True,
        schema_versions=tuple(supported_versions()),
    ))
    _save_registry(path, registry)
    payload = {"joined": True, "node_id": node_id,
               "schema_versions": supported_versions(),
               "capability": registry.get(node_id).capability.to_dict(),
               "capacity": registry.aggregate_capacity()}
    return _emit(args, payload, f"joined cluster as {node_id}")


def cmd_leave(args) -> int:
    """N9-R20: announce departure and remove self from the routing table."""
    _check_key(args.cluster_key, args.node_id)
    path = _state_path(args)
    registry = _load_registry(path)
    if registry.get(args.node_id) is None:
        raise ClusterError(f"node {args.node_id!r} is not in the cluster")
    registry.remove(args.node_id)
    _save_registry(path, registry)
    payload = {"left": True, "node_id": args.node_id,
               "capacity": registry.aggregate_capacity()}
    return _emit(args, payload, f"node {args.node_id} left the cluster")


def cmd_status(args) -> int:
    """N9-R22: aggregate capacity — GPUs, models, workers, memory."""
    path = _state_path(args)
    registry = _load_registry(path)
    nodes = registry.nodes(states=("active", "leaving", "failed"))
    payload = {
        "nodes": [n.to_dict() for n in nodes],
        "capacity": registry.aggregate_capacity(),
    }
    cap = payload["capacity"]
    human = (f"cluster: {cap['nodes']} node(s), {cap['total_gpus']} GPU(s), "
             f"{cap['total_models']} model(s), {cap['total_workers']} worker(s), "
             f"{cap['total_memory_bytes']} bytes memory")
    return _emit(args, payload, human)


def _add_common(p, key_required=True):
    p.add_argument("--json", action="store_true",
                   help="Machine-readable JSON output")
    p.add_argument("--state-file", help=f"Cluster state file (default {DEFAULT_STATE})")
    if key_required:
        p.add_argument("--cluster-key", required=True,
                       help="Shared cluster key (HMAC authentication)")


def _add_capability_args(p):
    p.add_argument("--model", action="append", help="Advertised model (repeatable)")
    p.add_argument("--tokens-per-second", type=float, default=0.0)
    p.add_argument("--context-window", type=int, default=0)
    p.add_argument("--memory-bytes", type=int, default=0)
    p.add_argument("--gpus", type=int, default=0)
    p.add_argument("--workers", type=int, default=1)


def node_main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="residual node",
                                     description="Manage this node's cluster membership")
    sub = parser.add_subparsers(dest="node_command", required=True)
    join = sub.add_parser("join", help="Join the cluster and accept tasks")
    _add_common(join)
    _add_capability_args(join)
    join.add_argument("--node-id")
    join.add_argument("--address")
    leave = sub.add_parser("leave", help="Finish in-flight work and leave the cluster")
    _add_common(leave)
    leave.add_argument("--node-id", required=True)
    args = parser.parse_args(argv)
    try:
        return {"join": cmd_join, "leave": cmd_leave}[args.node_command](args)
    except (ClusterError, OSError, ValueError) as exc:
        print(f"residual node: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def cluster_main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="residual cluster",
                                     description="Inspect cluster capacity and membership")
    sub = parser.add_subparsers(dest="cluster_command", required=True)
    status = sub.add_parser("status", help="Aggregate capacity and node roster")
    _add_common(status, key_required=False)
    args = parser.parse_args(argv)
    try:
        return cmd_status(args)
    except (ClusterError, OSError, ValueError) as exc:
        print(f"residual cluster: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
