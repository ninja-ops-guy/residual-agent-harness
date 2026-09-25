"""Remote inference runner. The coordinator performs all code execution and review."""
from __future__ import annotations

import argparse
import json
import os
import threading
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict

from residual.core import ContractError, canonical, strict_json
from residual.providers import NoRedirect
from .models import StationProvider
from .service import FILES_SCHEMA, RUNNER_SYSTEM


class WorkerClient:
    def __init__(self, station, token):
        url = urllib.parse.urlsplit(station)
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}):
            raise ContractError("Use HTTPS for remote stations or a loopback SSH tunnel")
        if url.username or url.password or url.query or url.fragment:
            raise ContractError("Station URL must not contain credentials, query, or fragment")
        if not token:
            raise ContractError("Set RESIDUAL_WORKER_TOKEN from Diagnostics → Connect another runner")
        self.base, self.token = station.rstrip("/"), token
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, route, data):
        req = urllib.request.Request(self.base + "/api/worker/" + route, data=canonical(data).encode(),
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        with self.opener.open(req, timeout=600) as r:
            value = r.read(500_001)
            if len(value) > 500_000:
                raise ContractError("Worker packet is too large")
            return strict_json(value.decode())

    def fetch(self, route, params=None):
        suffix = "?" + urllib.parse.urlencode(params or {}) if params else ""
        req = urllib.request.Request(self.base + "/api/worker/" + route + suffix,
            headers={"Authorization": "Bearer " + self.token})
        with self.opener.open(req, timeout=60) as r:
            value = r.read(500_001)
            if len(value) > 500_000:
                raise ContractError("Worker packet is too large")
            return strict_json(value.decode())

    def comms(self, project, after=0, thread_id=None):
        params = {"project_id": project, "after": after}
        if thread_id:
            params["thread_id"] = thread_id
        return self.fetch("comms", params).get("messages", [])

    def say(self, project, name, message, audience="all", thread_id="main"):
        return self.request("comms", {"project_id": project, "name": name, "message": message,
                                      "audience": audience, "thread_id": thread_id})

    def run_once(self, project, name, provider, max_tokens=4096, presence_ttl_s=90):
        work = self.request("claim", {"project_id": project, "name": name,
            "model": provider.model, "placement": provider.placement,
            "presence_ttl_s": presence_ttl_s}).get("work")
        if not work:
            return False
        stop = threading.Event()
        envelope = {"project_id": project, "task_id": work["task_id"], "lease": work["lease"],
                    "presence_ttl_s": presence_ttl_s}
        def heartbeat():
            while not stop.wait(60):
                try:
                    self.request("heartbeat", envelope)
                except Exception:
                    stop.set()
        threading.Thread(target=heartbeat, daemon=True).start()
        try:
            if provider.placement == "remote" and not work.get("allow_cloud"):
                raise ContractError("This mission does not permit cloud inference")
            reply = provider.generate(work["packet"], max_tokens)
            response = strict_json(reply.text)
            usage = {**asdict(reply.usage), "source": "worker_reported", "placement": "cloud" if provider.placement == "remote" else "local",
                     "role": "remote_runner", "model": provider.model, "request_bytes": provider.wire_size(work["packet"], max_tokens)}
            data = {**envelope, "submission_id": uuid.uuid4().hex, "response": response, "usage": usage}
            # A transport retry repeats the same idempotency key and exact proposal.
            try:
                self.request("result", data)
            except (OSError, TimeoutError):
                self.request("result", data)
        except Exception:
            # Empty proposals fail closed and produce a repair task, never a completion claim.
            try:
                self.request("result", {**envelope, "submission_id": uuid.uuid4().hex, "response": {"files": {}}})
            except Exception:
                pass
            raise
        finally:
            stop.set()
        return True


def main(argv=None):
    p = argparse.ArgumentParser(description="Connect a distributed RESIDUAL inference runner")
    p.add_argument("--station", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--name", default="remote-runner")
    p.add_argument("--kind", choices=["ollama", "openai_compatible", "openai", "anthropic", "google", "azure", "bedrock"], default="ollama")
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--base-url", default="")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--api-version", default="2024-10-21")
    p.add_argument("--placement", choices=["local", "remote"], default="local")
    p.add_argument("--once", action="store_true")
    p.add_argument("--poll-seconds", type=int, default=10)
    p.add_argument("--say", default="", help="Post one message to Shared Comms before polling for work")
    p.add_argument("--audience", choices=["all", "operator"], default="all", help="Audience for --say")
    p.add_argument("--thread", default="main", help="Shared Comms thread to read/post (default: main)")
    args = p.parse_args(argv)
    if not 1 <= args.poll_seconds <= 300:
        p.error("poll-seconds must be 1–300")
    client = WorkerClient(args.station, os.environ.get("RESIDUAL_WORKER_TOKEN", ""))
    provider = StationProvider({"kind": args.kind, "model": args.model, "base_url": args.base_url, "placement": args.placement, "region": args.region, "api_version": args.api_version},
                               RUNNER_SYSTEM, FILES_SCHEMA, os.environ.get("RESIDUAL_RUNNER_API_KEY"))
    if args.say:
        client.say(args.project, args.name, args.say, args.audience, args.thread)
        print("Shared Comms message posted.", flush=True)
        if args.once:
            return 0
    print("Runner connected. Waiting for ready tasks; Shared Comms is advisory and polling does not invoke an LLM.", flush=True)
    chat_after = 0
    while True:
        try:
            messages = client.comms(args.project, chat_after, args.thread)
            for message in messages:
                chat_after = max(chat_after, int(message.get("seq", 0)))
                print(f"[shared #{message.get('seq')}] {message.get('actor')}: {message.get('message')}", flush=True)
            presence_ttl_s = min(900, max(30, args.poll_seconds * 3 + 15))
            worked = client.run_once(args.project, args.name, provider, presence_ttl_s=presence_ttl_s)
            if worked:
                print("Candidate submitted. The station owns verification and review.", flush=True)
        except Exception as e:
            print(str(e) if isinstance(e, ContractError) else "Runner request failed. Check connectivity and model configuration.", flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
