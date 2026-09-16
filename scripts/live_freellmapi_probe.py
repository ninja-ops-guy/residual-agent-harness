#!/usr/bin/env python3
"""Bootstrap a localhost-only FreeLLMAPI and prove one real routed completion.

The runner stores no dashboard/session/unified credentials in retained evidence.
It is intended for an ephemeral CI workspace using keyless FreeLLMAPI providers.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(url: str, *, method: str = "GET", body: dict | None = None, bearer: str | None = None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
        return resp.status, dict(resp.headers.items()), json.loads(raw.decode("utf-8"))


def wait_ready(base: str, log_path: Path) -> None:
    last = None
    for _ in range(90):
        try:
            status, _, payload = request(f"{base}/api/auth/status")
            if status == 200:
                return
        except Exception as exc:  # noqa: BLE001 - retained in failure report only
            last = repr(exc)
        time.sleep(1)
    tail = ""
    if log_path.exists():
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    raise RuntimeError(f"FreeLLMAPI did not become ready: {last}\n{tail}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--freellmapi-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    base = "http://127.0.0.1:3001"
    log_path = out / "server.log"

    env = os.environ.copy()
    env.update(
        {
            "ENCRYPTION_KEY": secrets.token_hex(32),
            "FREEAPI_DB_PATH": str((out / "freellmapi.db").resolve()),
            "HOST": "127.0.0.1",
            "PORT": "3001",
            "REQUEST_ANALYTICS_RETENTION_DAYS": "0",
            "REQUEST_ANALYTICS_MAX_ROWS": "0",
            "FALLBACK_TIME_BUDGET_MS": "120000",
        }
    )
    server = subprocess.Popen(
        ["node", "server/dist/index.js"],
        cwd=args.freellmapi_dir,
        env=env,
        stdout=log_path.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_ready(base, log_path)
        password = secrets.token_urlsafe(24)
        _, _, setup = request(
            f"{base}/api/auth/setup",
            method="POST",
            body={"email": "residual-research@example.invalid", "password": password},
        )
        admin = setup["token"]
        _, _, key_payload = request(f"{base}/api/settings/api-key", bearer=admin)
        unified = key_payload["apiKey"]

        configured = []
        for platform in ("kilo", "ovh"):
            try:
                status, _, payload = request(
                    f"{base}/api/keys",
                    method="POST",
                    bearer=admin,
                    body={"platform": platform, "label": "RESIDUAL ephemeral research"},
                )
                configured.append({"platform": platform, "status": status, "modelsAvailable": payload.get("modelsAvailable")})
            except urllib.error.HTTPError as exc:
                configured.append({"platform": platform, "status": exc.code, "error": exc.read().decode("utf-8", errors="replace")[:500]})

        _, _, models = request(f"{base}/v1/models", bearer=unified)
        status, headers, completion = request(
            f"{base}/v1/chat/completions",
            method="POST",
            bearer=unified,
            body={
                "model": "auto:fast",
                "messages": [{"role": "user", "content": "Return exactly LIVE_OK and nothing else."}],
                "temperature": 0,
                "max_tokens": 32,
            },
        )
        content = completion["choices"][0]["message"]["content"].strip()
        routed = headers.get("x-routed-via") or headers.get("X-Routed-Via")
        result = {
            "schema_version": 1,
            "status": "PASS" if status == 200 and content == "LIVE_OK" else "FAIL",
            "http_status": status,
            "content": content,
            "routed_via": routed,
            "configured_keyless_providers": configured,
            "model_count": len(models.get("data", [])) if isinstance(models, dict) else None,
            "freellmapi_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.freellmapi_dir, text=True).strip(),
            "credentials_retained": False,
        }
        (out / "probe-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 2
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
