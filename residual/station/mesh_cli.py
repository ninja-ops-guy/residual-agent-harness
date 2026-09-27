"""Host-side CLI for a scoped SPEC-SC-MESH-001 worker."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

from residual.core import ContractError, strict_json
from .claw_adapter import OpenClawExecAdapter
from .mesh_runner import MeshClawRunner
from .mesh_worker import MeshWorkerClient


def _token():
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if directory:
        path = Path(directory) / "mesh-token"
        if path.is_file() and not path.is_symlink():
            token = path.read_text(encoding="utf-8").strip()
            if token:
                return token
    token = os.environ.get("RESIDUAL_MESH_TOKEN", "").strip()
    if not token:
        raise ContractError("Mesh token must come from systemd credentials or RESIDUAL_MESH_TOKEN")
    return token


def load_worker_config(path):
    value = strict_json(Path(path).read_text(encoding="utf-8"))
    required = {"schema", "station", "project_id", "worker_id", "outbox_path",
                "poll_seconds", "provider_routes", "adapter"}
    if not isinstance(value, dict) or set(value) != required:
        raise ContractError("Mesh worker config fields do not match the pinned schema")
    if value["schema"] != "residual.sc.mesh.worker/1":
        raise ContractError("Unsupported mesh worker config schema")
    if type(value["poll_seconds"]) is not int or not 1 <= value["poll_seconds"] <= 300:
        raise ContractError("poll_seconds must be 1-300")
    routes = value["provider_routes"]
    if not isinstance(routes, list) or not 1 <= len(routes) <= 5:
        raise ContractError("provider_routes must contain 1-5 routes")
    for route in routes:
        if (not isinstance(route, dict) or set(route) != {"placement", "model"}
                or route["placement"] not in {"local", "remote"}
                or not isinstance(route["model"], str) or not route["model"]):
            raise ContractError("Invalid provider route")
    adapter = value["adapter"]
    allowed = {"kind", "config_path", "workspace", "expected_version", "timeout_s"}
    if not isinstance(adapter, dict) or set(adapter) != allowed or adapter["kind"] != "openclaw-exec":
        raise ContractError("Unsupported claw adapter configuration")
    return value


def worker_main(argv=None):
    parser = argparse.ArgumentParser(description="Run one scoped RESIDUAL mesh worker")
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    runner = None
    stopping = False
    try:
        cfg = load_worker_config(args.config)
        adapter_cfg = cfg["adapter"]
        adapter = OpenClawExecAdapter(
            config_path=adapter_cfg["config_path"],
            workspace=adapter_cfg["workspace"],
            expected_version=adapter_cfg["expected_version"] or None,
            timeout_s=adapter_cfg["timeout_s"],
        )
        discovery = adapter.connect()
        if args.preflight:
            print(json.dumps({"status": "PREFLIGHT_PASS", "adapter": discovery,
                              "project_id": cfg["project_id"], "worker_id": cfg["worker_id"]},
                             sort_keys=True))
            return 0
        client = MeshWorkerClient(
            cfg["station"], _token(), worker_id=cfg["worker_id"],
            outbox_path=cfg["outbox_path"])
        runner = MeshClawRunner(
            client, adapter, project_id=cfg["project_id"],
            provider_routes=cfg["provider_routes"])
        runner.synchronize()

        def stop(signum, frame):
            nonlocal stopping
            stopping = True
            if runner is not None:
                try:
                    runner.cancel_current()
                except Exception:
                    pass
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        while not stopping:
            try:
                result = runner.run_once()
                if result:
                    print(json.dumps({"status": "RESULT_SUBMITTED",
                                      "project_id": cfg["project_id"]}, sort_keys=True), flush=True)
            except ContractError as exc:
                print(json.dumps({"status": "BLOCKED", "reason": str(exc)[:300]}, sort_keys=True),
                      file=sys.stderr, flush=True)
                if args.once:
                    return 3
            except Exception:
                print(json.dumps({"status": "ERROR", "reason": "worker_execution_failed"},
                                 sort_keys=True), file=sys.stderr, flush=True)
                if args.once:
                    return 2
            if args.once:
                return 0
            if not stopping:
                time.sleep(cfg["poll_seconds"])
        return 0
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "ERROR", "reason": type(exc).__name__}, sort_keys=True),
              file=sys.stderr)
        return 2
    finally:
        if runner is not None:
            try:
                runner.shutdown()
            except Exception:
                pass
