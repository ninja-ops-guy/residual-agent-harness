"""Remote inference runner. The coordinator performs all code execution and review."""
from __future__ import annotations

import argparse
import json
import os
import queue
import sys
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


class WorkerAuthorityLost(ContractError):
    """The runner can no longer prove that it still owns the claimed work."""


class WorkerClient:
    def __init__(self, station, token, heartbeat_interval=60.0, heartbeat_grace=180.0):
        url = urllib.parse.urlsplit(station)
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}):
            raise ContractError("Use HTTPS for remote stations or a loopback SSH tunnel")
        if url.username or url.password or url.query or url.fragment:
            raise ContractError("Station URL must not contain credentials, query, or fragment")
        if not token:
            raise ContractError("Set RESIDUAL_WORKER_TOKEN from Diagnostics → Connect another runner")
        if heartbeat_interval <= 0 or heartbeat_grace < heartbeat_interval:
            raise ContractError("Heartbeat grace must be at least one heartbeat interval")
        self.base, self.token = station.rstrip("/"), token
        self.heartbeat_interval = float(heartbeat_interval)
        self.heartbeat_grace = float(heartbeat_grace)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, route, data):
        req = urllib.request.Request(self.base + "/api/worker/" + route, data=canonical(data).encode(),
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        with self.opener.open(req, timeout=600) as r:
            value = r.read(500_001)
            if len(value) > 500_000:
                raise ContractError("Worker packet is too large")
            return strict_json(value.decode())

    def _generate_with_authority(self, provider, packet, max_tokens, envelope, stop):
        """Run inference while separately proving lease continuity.

        Provider transports are not assumed to support cooperative cancellation. If the
        heartbeat grace is exceeded, the worker process surrenders authority immediately,
        never submits the eventual proposal, and the CLI exits so daemon inference cannot
        outlive the authority boundary indefinitely.
        """
        authority_lost = threading.Event()
        finished = queue.Queue(maxsize=1)
        last_success = [time.monotonic()]

        def heartbeat():
            while not stop.wait(self.heartbeat_interval):
                try:
                    self.request("heartbeat", envelope)
                    last_success[0] = time.monotonic()
                except Exception:
                    if time.monotonic() - last_success[0] >= self.heartbeat_grace:
                        authority_lost.set()
                        return

        def generate():
            try:
                finished.put((True, provider.generate(packet, max_tokens)))
            except BaseException as exc:  # preserve provider exception identity for caller
                finished.put((False, exc))

        threading.Thread(target=heartbeat, daemon=True).start()
        threading.Thread(target=generate, daemon=True).start()
        while True:
            if authority_lost.wait(0.05):
                raise WorkerAuthorityLost("Runner authority was surrendered after persistent heartbeat loss")
            try:
                ok, value = finished.get_nowait()
            except queue.Empty:
                continue
            if ok:
                return value
            raise value

    def run_once(self, project, name, provider, max_tokens=4096):
        work = self.request("claim", {"project_id": project, "name": name}).get("work")
        if not work:
            return False
        stop = threading.Event()
        envelope = {"project_id": project, "task_id": work["task_id"], "lease": work["lease"]}
        try:
            if provider.placement == "remote" and not work.get("allow_cloud"):
                raise ContractError("This mission does not permit cloud inference")
            reply = self._generate_with_authority(provider, work["packet"], max_tokens, envelope, stop)
            response = strict_json(reply.text)
            usage = {**asdict(reply.usage), "source": "worker_reported", "placement": "cloud" if provider.placement == "remote" else "local",
                     "role": "remote_runner", "model": provider.model, "request_bytes": provider.wire_size(work["packet"], max_tokens)}
            data = {**envelope, "submission_id": uuid.uuid4().hex, "response": response, "usage": usage}
            # A transport retry repeats the same idempotency key and exact proposal.
            try:
                self.request("result", data)
            except (OSError, TimeoutError):
                self.request("result", data)
        except WorkerAuthorityLost:
            # Never attempt a proposal after the authority continuity proof has failed.
            raise
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
    args = p.parse_args(argv)
    if not 1 <= args.poll_seconds <= 300:
        p.error("poll-seconds must be 1–300")
    client = WorkerClient(args.station, os.environ.get("RESIDUAL_WORKER_TOKEN", ""))
    provider = StationProvider({"kind": args.kind, "model": args.model, "base_url": args.base_url, "placement": args.placement, "region": args.region, "api_version": args.api_version},
                               RUNNER_SYSTEM, FILES_SCHEMA, os.environ.get("RESIDUAL_RUNNER_API_KEY"))
    print("Runner connected. Waiting for ready tasks; polling does not invoke an LLM.", flush=True)
    while True:
        try:
            worked = client.run_once(args.project, args.name, provider)
            if worked:
                print("Candidate submitted. The station owns verification and review.", flush=True)
        except WorkerAuthorityLost as e:
            print(str(e), file=sys.stderr, flush=True)
            return 1
        except Exception as e:
            print(str(e) if isinstance(e, ContractError) else "Runner request failed. Check connectivity and model configuration.", flush=True)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
