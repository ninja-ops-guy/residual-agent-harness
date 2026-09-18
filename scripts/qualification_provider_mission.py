#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from residual.core import canonical
from residual.station.models import PROVIDERS, save_settings
from residual.station.service import Station

SPEC = """# Live provider qualification mission

The provider must implement one bounded function and then independently review
the resulting candidate. Deterministic checks, Station review binding, integration
and release export remain authoritative.

```json
{
  "schema_version": 1,
  "name": "Live Provider Qualification",
  "goal": "Implement a tiny deterministic arithmetic module.",
  "tasks": [
    {
      "id": "LIVE-1",
      "title": "Implement add",
      "instruction": "Implement add(a, b) in app.py. It must return the Python sum a + b for integers and floats. Do not add unrelated files.",
      "files": ["app.py"],
      "context": [],
      "depends_on": [],
      "route": "cloud",
      "checks": [
        {"kind": "python_compile", "path": "app.py"},
        {"kind": "command", "argv": ["{python}", "-c", "from app import add; assert add(2, 3) == 5; assert add(-4, 1) == -3; assert add(1.5, 2.25) == 3.75"], "timeout": 30}
      ]
    }
  ]
}
```
"""


def profile(provider: str, model: str, base_url: str | None) -> dict:
    if provider not in {"openai", "openai_compatible", "anthropic", "google"}:
        raise ValueError("full mission supports openai, openai_compatible, anthropic or google")
    default = PROVIDERS[provider]["base_url"]
    return {
        "kind": provider,
        "model": model,
        "base_url": base_url or default,
        "output_token_field": "max_completion_tokens",
    }


def run_mission(*, provider: str, model: str, base_url: str | None, root: Path) -> dict:
    if provider != "openai_compatible" and not os.environ.get("RESIDUAL_CLOUD_API_KEY"):
        return {
            "schema": "residual.qualification.provider-mission.v1",
            "result": "UNKNOWN",
            "provider": provider,
            "model": model,
            "reason": "RESIDUAL_CLOUD_API_KEY is absent",
            "non_claim": "No fixture result is substituted for missing live-provider credentials.",
        }

    started = time.monotonic()
    station = Station(root)
    save_settings(station.store, {
        "cloud": profile(provider, model, base_url),
        "review_placement": "cloud",
        "max_output_tokens": 4096,
    })
    pid = station.create(SPEC, allow_cloud=True, commands=True)
    try:
        station.triage(pid)
        if station.store.task(pid, "LIVE-1")["state"] != "ready":
            raise RuntimeError("triage did not produce a ready task")

        run = station.run_one(pid, "LIVE-1", owner="live-provider-qualification")
        if not run or station.store.task(pid, "LIVE-1")["state"] != "review_ready":
            raise RuntimeError("live implementation did not reach review_ready")

        review = station.review(pid, "LIVE-1")
        if review.get("approved") is not True or station.store.task(pid, "LIVE-1")["state"] != "approved":
            raise RuntimeError("live reviewer did not approve the verified candidate")

        integrated = station.integrate(pid, "LIVE-1")
        if station.store.task(pid, "LIVE-1")["state"] != "integrated":
            raise RuntimeError("verified candidate did not integrate")

        release = station.export(pid)
        meta, release_bytes = station.store.artifact(release["id"])
        task = station.store.task(pid, "LIVE-1")
        metrics = station.metrics(pid)
        return {
            "schema": "residual.qualification.provider-mission.v1",
            "result": "PASS",
            "provider": provider,
            "model_requested": model,
            "project_id": pid,
            "integrated_head": integrated["head_commit"],
            "verification_receipt_hash": task["verification_receipt"]["receipt"]["receipt_hash"],
            "release": {
                "id": release["id"],
                "name": meta["name"],
                "sha256": hashlib.sha256(release_bytes).hexdigest(),
                "size": len(release_bytes),
            },
            "metrics": metrics,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            "non_claim": "PASS establishes one exact-revision end-to-end provider mission; it does not establish general model quality or long-run provider reliability.",
        }
    except Exception as exc:
        retained = station.store.observation_export(pid)
        return {
            "schema": "residual.qualification.provider-mission.v1",
            "result": "FAIL",
            "provider": provider,
            "model_requested": model,
            "project_id": pid,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "observation_sha256": hashlib.sha256(retained.encode("utf-8")).hexdigest(),
            "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            "non_claim": "The live failure is retained; no scripted provider fallback is substituted.",
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run one full live-provider RESIDUAL mission")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)

    if args.root:
        args.root.mkdir(parents=True, exist_ok=True)
        report = run_mission(provider=args.provider, model=args.model, base_url=args.base_url, root=args.root)
    else:
        with tempfile.TemporaryDirectory(prefix="residual-live-provider-mission-") as temp:
            report = run_mission(provider=args.provider, model=args.model, base_url=args.base_url, root=Path(temp))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else (2 if report["result"] == "UNKNOWN" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
