"""Live qualification for Residual-managed FreeLLMAPI.

This deliberately uses the real pinned container image while avoiding paid model
calls. It proves the local service boundary, bootstrap credential scrub, and the
Residual privacy-routing behavior produced by the managed config.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from residual.config import build_harness, load_config
from residual.core import Artifact, Obligation, Task
from residual.onboarding import (
    FREELLMAPI_IMAGE,
    ManagedPaths,
    start_service,
    wait_for_http,
    write_managed_config,
    write_unified_key,
)


BOOTSTRAP_MARKER = "residual-qualification-bootstrap-secret"


def run(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=180, check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {command[0]} {command[1] if len(command) > 1 else ''}")
    return result


def container_inspect(paths: ManagedPaths) -> dict:
    container_id = run(
        ["docker", "compose", "ps", "-q", "freellmapi"], cwd=paths.service_dir,
    ).stdout.strip()
    if not container_id:
        raise RuntimeError("FreeLLMAPI container is not running")
    payload = json.loads(run(["docker", "inspect", container_id]).stdout)
    if not isinstance(payload, list) or len(payload) != 1:
        raise RuntimeError("unexpected docker inspect result")
    return payload[0]


def assert_scrubbed(inspect: dict) -> None:
    env = inspect.get("Config", {}).get("Env") or []
    if any(BOOTSTRAP_MARKER in value for value in env):
        raise RuntimeError("bootstrap credential remained in container environment")
    config_values = [value for value in env if value.startswith("FREEAPI_CONFIG_JSON=")]
    if any(value != "FREEAPI_CONFIG_JSON=" for value in config_values):
        raise RuntimeError("FREEAPI_CONFIG_JSON remained populated after bootstrap")


def assert_loopback_only(inspect: dict) -> list[dict]:
    bindings = (inspect.get("HostConfig", {}).get("PortBindings") or {}).get("3001/tcp") or []
    if not bindings:
        raise RuntimeError("FreeLLMAPI port 3001 is not published")
    if any(binding.get("HostIp") not in {"127.0.0.1", "::1"} for binding in bindings):
        raise RuntimeError("FreeLLMAPI is published beyond loopback")
    return bindings


def privacy_regression(paths: ManagedPaths) -> dict:
    # The client key value is never used: the remote provider must be rejected
    # before network I/O because the declared evidence is private.
    write_unified_key(paths, "qualification-client-key-not-used")
    write_managed_config(paths, model="auto")
    config = load_config(paths.config)
    if config["expert"].get("placement") != "remote":
        raise RuntimeError("managed FreeLLMAPI provider is not remote-classified")

    harness = build_harness(config, mode="full_cloud", disable_cache=True)
    task = Task(
        "freellmapi-privacy-qualification",
        "Prove private evidence cannot cross the managed FreeLLMAPI boundary.",
        {"private": Artifact("private", "[1,2,3]\n", cloud=False)},
        (
            Obligation(
                "sum", "Return the sum of the private values.", "json_sum",
                ("private",), parameters={"artifact": "private"}, cloud=True,
            ),
        ),
    )
    result = harness.run(task)
    unresolved = result["unresolved"].get("sum") or {}
    if unresolved.get("code") != "local_only":
        raise RuntimeError("private obligation was not blocked as local_only")
    if result["metrics"]["remote_calls"] != 0 or result["metrics"]["remote_request_bytes"] != 0:
        raise RuntimeError("privacy rejection occurred after remote I/O was reserved")
    return {
        "provider_placement": config["expert"]["placement"],
        "verdict": unresolved.get("code"),
        "remote_calls": result["metrics"]["remote_calls"],
        "remote_request_bytes": result["metrics"]["remote_request_bytes"],
    }


def qualify(home: Path, output: Path) -> dict:
    paths = ManagedPaths.from_value(home)
    bootstrap = {
        "keys": [
            {
                "platform": "groq",
                "key": BOOTSTRAP_MARKER,
                "label": "residual-qualification",
            }
        ],
        "routing": {"strategy": "balanced"},
    }

    ok, detail = start_service(paths, bootstrap)
    if not ok:
        raise RuntimeError(f"managed service bootstrap failed: {detail}")
    if not wait_for_http("http://127.0.0.1:3001/", timeout=60):
        raise RuntimeError("scrubbed FreeLLMAPI service did not become reachable")

    inspect = container_inspect(paths)
    assert_scrubbed(inspect)
    bindings = assert_loopback_only(inspect)
    configured_image = inspect.get("Config", {}).get("Image")
    if configured_image != FREELLMAPI_IMAGE:
        raise RuntimeError("running container does not use the reviewed immutable image reference")

    privacy = privacy_regression(paths)
    evidence = {
        "schema_version": "residual.freellmapi.qualification.v1",
        "git_sha": os.environ.get("GITHUB_SHA"),
        "image_reference": FREELLMAPI_IMAGE,
        "container_image_reference": configured_image,
        "container_image_id": inspect.get("Image"),
        "loopback_bindings": bindings,
        "service_reachable_after_scrub": True,
        "bootstrap_environment_scrubbed": True,
        "privacy_routing": privacy,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    output = Path(os.environ.get("RESIDUAL_QUALIFICATION_OUTPUT", "runs/freellmapi-qualification.json"))
    requested_home = os.environ.get("RESIDUAL_QUALIFICATION_HOME")
    temporary = tempfile.TemporaryDirectory() if requested_home is None else None
    home = Path(requested_home) if requested_home else Path(temporary.name)
    paths = ManagedPaths.from_value(home)
    try:
        evidence = qualify(home, output)
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"FreeLLMAPI qualification failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        if paths.service_dir.exists():
            run(["docker", "compose", "down", "--volumes", "--remove-orphans"],
                cwd=paths.service_dir, check=False)
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
