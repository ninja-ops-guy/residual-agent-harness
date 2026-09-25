#!/usr/bin/env python3
"""Bounded AUD-1 F6 stale-result rejection probe.

Run only after Case B has naturally expired/recovered and a different runner owns the
task. The worker credential is read from the environment and is never written to the
result artifact. The probe submits one harmless stale result attempt and succeeds only
when Station rejects it with HTTP 403.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import secrets
import urllib.error
import urllib.request

SCHEMA = "residual.aud1.f6.stale-probe.v2"\nSTALE_REJECTION_TEXT = "Task authority belongs to another runner"


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sanitize_response_excerpt(text, *secret_values):
    """Retain only the denial class; never retain server-controlled response text."""
    if STALE_REJECTION_TEXT in str(text):
        return STALE_REJECTION_TEXT
    return "<redacted-response>"


def main(argv=None):
    p = argparse.ArgumentParser(description="Attempt one stale worker result and require HTTP 403")
    p.add_argument("--station-url", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--lease", required=True)
    p.add_argument("--attempt", required=True, type=int)
    p.add_argument("--owner", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--token-env", default="RESIDUAL_WORKER_TOKEN")
    args = p.parse_args(argv)

    token = os.environ.get(args.token_env, "")
    if not token:
        raise SystemExit(f"REFUSE: {args.token_env} is not set")

    submission_id = "f6-stale-" + secrets.token_hex(8)
    # The live Station API requires the original raw lease. Attempt/owner are
    # evidence bindings only and are deliberately not added to the wire schema.
    body = {
        "project_id": args.project,
        "task_id": args.task,
        "lease": args.lease,
        "submission_id": submission_id,
        "response": {"files": {}},
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        args.station_url.rstrip("/") + "/api/worker/result",
        data=raw,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "residual-aud1-f6-stale-probe/1",
        },
    )

    status = None
    response_text = ""
    accepted = False
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=15) as response:
            status = response.status
            response_text = response.read(4096).decode("utf-8", "replace")
            accepted = 200 <= status < 300
    except urllib.error.HTTPError as exc:
        status = exc.code
        response_text = exc.read(4096).decode("utf-8", "replace")
    except Exception as exc:
        response_text = f"{type(exc).__name__}: {exc}"

    rejected = status == 403
    response_excerpt = sanitize_response_excerpt(response_text, args.lease, token)
    record = {
        "schema": SCHEMA,
        "captured_at": utcnow(),
        "station_url": args.station_url.rstrip("/"),
        "project_id": args.project,
        "task_id": args.task,
        "lease_fingerprint": "sha256:" + hashlib.sha256(args.lease.encode("utf-8")).hexdigest(),
        "attempt": args.attempt,
        "owner": args.owner,
        "submission_id": submission_id,
        "credential_source": args.token_env,
        "credential_value_retained": False,
        "expected_status": 403,
        "observed_status": status,
        "accepted": accepted,
        "rejected": rejected,
        "response_excerpt": response_excerpt,
    }
    path = pathlib.Path(args.output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if rejected and not accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
