"""Counterexample-directed residual delegation, with evidence pull and frozen results."""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from .core import Context, ContractError, Registry, Task, Verdict, canonical, digest, positive_int, strict_json
from .providers import Provider, ProviderError, Reply
from .storage import Cache, Ledger


@dataclass(frozen=True)
class Limits:
    local_rounds: int = 2
    expert_rounds: int = 4
    max_calls: int = 24
    max_expert_calls: int = 12
    max_remote_input_bytes: int = 500_000
    max_request_bytes: int = 200_000
    max_output_tokens: int = 2048
    max_requested_lines: int = 100
    seed_lines: int = 3

    def __post_init__(self):
        for key, value in asdict(self).items():
            positive_int(value, key, allow_zero=key in {"local_rounds", "expert_rounds", "max_expert_calls", "max_remote_input_bytes", "seed_lines"})


MODES = {"residual", "residual_fixed", "cascade", "full_cloud", "local_only", "no_pull"}


class Harness:
    def __init__(self, registry: Registry, local: Provider | None, expert: Provider | None,
                 limits: Limits | None = None, cache: Cache | None = None, mode="residual"):
        if mode not in MODES:
            raise ContractError("unknown routing mode")
        for provider in (local, expert):
            if provider is not None and provider.placement not in {"local", "remote"}:
                raise ContractError("providers must declare local or remote placement")
        self.registry, self.local, self.expert = registry, local, expert
        self.limits, self.cache, self.mode = limits or Limits(), cache, mode

    def run(self, task: Task) -> dict:
        start = time.monotonic()
        self.task = task
        self.accepted: dict[str, Any] = {}
        self.receipts: dict[str, dict] = {}
        self.failures: dict[str, dict] = {}
        self.windows = {}
        self.calls = []
        self.ledger = Ledger()
        self.cache_hits = 0
        self.deterministic_accepts = 0
        self.remote_bytes = 0
        self.expert_calls = 0
        for o in task.obligations:
            if o.check not in self.registry.checks or (o.solver and o.solver not in self.registry.solvers):
                raise ContractError("unregistered verifier or solver")
        self.ledger.add("run_started", run_id=str(uuid.uuid4()), task_id=task.id, mode=self.mode,
                        limits=asdict(self.limits), artifact_hashes={k: a.sha256 for k, a in task.artifacts.items()})
        attempted = set()
        while True:
            ready = [o.id for o in task.obligations if o.id not in self.accepted and o.id not in attempted
                     and set(o.depends_on) <= self.accepted.keys()]
            if not ready:
                break
            for node_id in ready:
                if self.cache:
                    hit, value = self.cache.get(self._cache_key(node_id))
                    if hit and self._accept(node_id, value, "cache"):
                        self.cache_hits += 1
                        continue
                o = task.by_id[node_id]
                if o.solver and self.mode != "full_cloud":
                    try:
                        value = self.registry.solvers[o.solver](self._context(node_id))
                        if self._accept(node_id, value, "deterministic"):
                            self.deterministic_accepts += 1
                    except Exception:
                        self._failure(node_id, "solver_error", "The local solver failed; use the declared evidence.")
            if self.mode != "full_cloud" and self.local:
                self._dispatch(self.local, ready, "local", self.limits.local_rounds)
            if self.mode != "local_only" and self.expert:
                self._dispatch(self.expert, ready, "expert", self.limits.expert_rounds)
            attempted.update(ready)
        unresolved = {}
        for o in task.obligations:
            if o.id in self.accepted:
                continue
            missing = [d for d in o.depends_on if d not in self.accepted]
            unresolved[o.id] = ({"code": "dependency_blocked", "dependencies": missing} if missing
                                else self.failures.get(o.id, {"code": "no_verified_candidate"}))
        remote_calls = [c for c in self.calls if c["placement"] == "remote"]
        reported = [c for c in remote_calls if c["usage"]["source"] == "reported"]
        priced = [c["cost_usd"] for c in remote_calls if c["cost_usd"] is not None]
        result = {
            "schema_version": "residual.run.v1", "task_id": task.id, "mode": self.mode,
            "status": "passed" if not unresolved else ("partial" if self.accepted else "blocked"),
            "success": not unresolved, "values": self.accepted, "unresolved": unresolved,
            "receipts": self.receipts,
            "metrics": {"calls": len(self.calls), "expert_calls": self.expert_calls,
                        "remote_calls": len(remote_calls), "remote_request_bytes": self.remote_bytes,
                        "remote_input_tokens_reported": sum(c["usage"]["input_tokens"] for c in reported),
                        "remote_output_tokens_reported": sum(c["usage"]["output_tokens"] for c in reported),
                        "remote_usage_complete": len(reported) == len(remote_calls),
                        "remote_cost_usd": sum(priced) if len(priced) == len(remote_calls) else None,
                        "remote_cost_known_subtotal_usd": sum(priced),
                        "cache_hits": self.cache_hits, "deterministic_accepts": self.deterministic_accepts,
                        "accepted_obligations": len(self.accepted), "total_obligations": len(task.obligations),
                        "elapsed_ms": (time.monotonic() - start) * 1000},
            "calls": self.calls}
        self.ledger.add("run_finished", result_sha256=digest(result), success=result["success"])
        return {**result, "trace_root": self.ledger.head}

    def _context(self, node_id):
        return Context(self.task.by_id[node_id], self.task.artifacts, self.accepted)

    def _binding(self, node_id):
        o = self.task.by_id[node_id]
        return {"contract_version": "residual.obligation.v1", "task_id": self.task.id, "goal": self.task.goal,
                "obligation": asdict(o), "check_revision": self.registry.checks[o.check][0],
                "evidence": {a: self.task.artifacts[a].sha256 for a in o.evidence},
                "dependencies": {d: self.receipts[d]["sha256"] for d in o.depends_on}}

    def _cache_key(self, node_id):
        return digest(self._binding(node_id))

    def _failure(self, node_id, code, message=""):
        self.failures[node_id] = {"code": code, "message": message}
        self.ledger.add("counterexample", obligation_id=node_id, code=code)

    def _accept(self, node_id, value, source):
        if node_id in self.accepted:
            raise ContractError("accepted obligation cannot be overwritten")
        try:
            # Defensive copies bind exactly what was checked, excluding NaN and aliases.
            original = canonical(value)
            verdict = self.registry.checks[self.task.by_id[node_id].check][1](strict_json(original), self._context(node_id))
            if not isinstance(verdict, Verdict):
                verdict = Verdict("unknown", "invalid_verifier_result")
        except Exception:
            verdict = Verdict("unknown", "verifier_error", "The host verifier could not establish this obligation.")
        self.ledger.add("verification", obligation_id=node_id, source=source, status=verdict.status, code=verdict.code)
        if verdict.status != "pass":
            self._failure(node_id, verdict.code, verdict.message)
            return False
        value = strict_json(original)
        receipt = {"binding": self._cache_key(node_id), "value_sha256": digest(value),
                   "verifier": self.task.by_id[node_id].check,
                   "revision": self.registry.checks[self.task.by_id[node_id].check][0]}
        receipt["sha256"] = digest(receipt)
        self.accepted[node_id], self.receipts[node_id] = value, receipt
        self.failures.pop(node_id, None)
        if self.cache and source != "cache":
            self.cache.put(self._cache_key(node_id), value)
        self.ledger.add("obligation_accepted", obligation_id=node_id, source=source, receipt=receipt)
        return True

    def _packet(self, provider, ids, role):
        remote = provider.placement == "remote"
        full = role == "expert" and self.mode in {"full_cloud", "cascade"}
        needed = set().union(*(set(self.task.by_id[n].evidence) for n in ids))
        # Full-context local expert calls also separate exportable/private work.
        local_public_call = not remote and all(self.task.cloud_allowed(n) for n in ids)
        artifact_ids = (set(self.task.artifacts) if full else needed)
        artifact_ids = {a for a in artifact_ids if not remote or self.task.artifacts[a].cloud}
        if local_public_call:
            artifact_ids = {a for a in artifact_ids if self.task.artifacts[a].cloud}
        manifest = [{"artifact_id": a, "sha256": self.task.artifacts[a].sha256,
                     "line_count": len(self.task.artifacts[a].lines)} for a in sorted(artifact_ids)]
        excerpts = []
        for artifact_id in sorted(artifact_ids):
            artifact = self.task.artifacts[artifact_id]
            if full:
                excerpts.append(artifact.excerpt(1, len(artifact.lines)))
                continue
            intervals = []
            if self.limits.seed_lines:
                intervals.append((1, min(self.limits.seed_lines, len(artifact.lines))))
            for node_id in ids:
                intervals.extend(self.windows.get((provider.name, node_id, artifact_id), []))
            for start, end in self._merge(intervals):
                excerpts.append(artifact.excerpt(start, end))
        deps = set().union(*(set(self.task.by_id[n].depends_on) for n in ids))
        if full:
            deps = set(self.accepted)
        dependencies = {d: {"value": self.accepted[d], "receipt": self.receipts[d]["sha256"]}
                        for d in sorted(deps) if (not remote and not local_public_call) or self.task.cloud_allowed(d)}
        packet = {"protocol": "residual.packet.v1", "task_id": self.task.id, "goal": self.task.goal,
                "obligations": [{"id": n, "instruction": self.task.by_id[n].instruction,
                                 "evidence_ids": list(self.task.by_id[n].evidence),
                                 "depends_on": list(self.task.by_id[n].depends_on)} for n in ids],
                "accepted_dependencies": dependencies,
                "counterexamples": {n: self.failures[n] for n in ids if n in self.failures},
                "manifest": manifest, "evidence": excerpts,
                "request_limits": {"max_lines": self.limits.max_requested_lines,
                                   "pull_enabled": self.mode != "no_pull"}}
        # A small complete capsule can cost less than even two framed requests.
        # This is a byte heuristic, not an assertion about tokenization or quality.
        plan = "full_context" if full else "seed_and_pull"
        if self.mode == "residual" and role == "expert":
            seed_size = provider.wire_size(packet, self.limits.max_output_tokens)
            raw_size = sum(len(self.task.artifacts[a].text.encode()) for a in needed)
            if raw_size <= 2 * seed_size:
                scoped = {**packet, "evidence": [self.task.artifacts[a].excerpt(1, len(self.task.artifacts[a].lines))
                                                for a in sorted(needed)]}
                scoped_size = provider.wire_size(scoped, self.limits.max_output_tokens)
                remaining = self.limits.max_remote_input_bytes - self.remote_bytes
                if (scoped_size <= 2 * seed_size and scoped_size <= self.limits.max_request_bytes
                        and (not remote or scoped_size <= remaining)):
                    packet, plan = scoped, "inline_complete_scoped_evidence"
        self.ledger.add("context_plan", role=role, plan=plan, obligation_ids=ids)
        return packet

    @staticmethod
    def _merge(intervals):
        merged = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        return merged

    def _dispatch(self, provider, ready, role, rounds):
        if provider.placement == "remote":
            self._work(provider, ready, role, rounds)
        else:
            # Never expose private evidence while generating an exportable value.
            public = [n for n in ready if self.task.cloud_allowed(n)]
            private = [n for n in ready if not self.task.cloud_allowed(n)]
            self._work(provider, public, role, rounds)
            self._work(provider, private, role, rounds)

    def _work(self, provider, ready, role, rounds):
        for _ in range(rounds):
            ids = [n for n in ready if n not in self.accepted]
            if provider.placement == "remote":
                for n in ids:
                    if not self.task.cloud_allowed(n):
                        self._failure(n, "local_only", "This obligation or its dependencies cannot be sent remotely.")
                ids = [n for n in ids if self.task.cloud_allowed(n)]
            if not ids:
                return
            packet = self._packet(provider, ids, role)
            size = provider.wire_size(packet, self.limits.max_output_tokens)
            if (len(self.calls) >= self.limits.max_calls or size > self.limits.max_request_bytes
                    or (role == "expert" and self.expert_calls >= self.limits.max_expert_calls)
                    or (provider.placement == "remote" and self.remote_bytes + size > self.limits.max_remote_input_bytes)):
                for n in ids:
                    self._failure(n, "budget_exhausted", "A call or request-body byte limit prevents the next request.")
                self.ledger.add("budget_blocked", role=role, request_bytes=size)
                return
            if provider.placement == "remote":
                self.remote_bytes += size
            if role == "expert":
                self.expert_calls += 1
            record = {"role": role, "provider": provider.name, "placement": provider.placement,
                      "obligation_ids": ids, "request_bytes": size, "packet_sha256": digest(packet),
                      "usage": {"input_tokens": None, "output_tokens": None,
                                "cached_input_tokens": None, "source": "unavailable"},
                      "cost_usd": None, "elapsed_ms": None, "error": None}
            # Reserve before I/O. Failed requests may still have incurred charges.
            self.calls.append(record)
            self.ledger.add("call_reserved", role=role, provider=provider.name, request_bytes=size,
                            packet_sha256=digest(packet), obligation_ids=ids)
            started = time.monotonic()
            try:
                reply = provider.generate(packet, self.limits.max_output_tokens)
                if not isinstance(reply, Reply):
                    raise ProviderError("invalid_reply_type")
            except Exception as exc:
                code = str(exc) if isinstance(exc, ProviderError) else "provider_exception"
                # Adapter error messages are fixed codes. Custom exceptions are never logged.
                if len(code) > 100 or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in code):
                    code = "provider_error"
                record["error"] = code
                record["elapsed_ms"] = (time.monotonic() - started) * 1000
                self.ledger.add("provider_failed", role=role, code=code)
                for n in ids:
                    self._failure(n, code, "The provider call failed; no candidate was accepted.")
                continue
            record["usage"], record["elapsed_ms"] = asdict(reply.usage), reply.elapsed_ms
            record["cost_usd"] = provider.prices.cost(reply.usage) if provider.prices else None
            self.ledger.add("call_completed", role=role, usage=record["usage"], elapsed_ms=reply.elapsed_ms,
                            response_sha256=digest(reply.text), finish_reason=reply.finish_reason)
            try:
                if reply.finish_reason in {"length", "max_tokens"}:
                    raise ContractError("truncated response")
                data = self._parse(reply.text, ids)
            except (ValueError, TypeError, KeyError, RecursionError):
                for n in ids:
                    self._failure(n, "invalid_protocol", "Return exactly the documented updates/requests JSON object.")
                continue
            for n, value in data["updates"].items():
                self._accept(n, value, role)
            for request in data["requests"]:
                self._request_evidence(provider, request)
            if not data["updates"] and not data["requests"]:
                for n in ids:
                    self._failure(n, "worker_abstained", "The worker returned no candidate or evidence request.")
                return

    def _parse(self, text, ids):
        if len(text.encode("utf-8")) > 2_000_000:
            raise ContractError("response too large")
        data = strict_json(text)
        if not isinstance(data, dict) or set(data) != {"updates", "requests"}:
            raise ContractError("invalid response keys")
        if not isinstance(data["updates"], dict) or not isinstance(data["requests"], list):
            raise ContractError("invalid response types")
        if set(data["updates"]) - set(ids) or len(data["requests"]) > 8:
            raise ContractError("response exceeds obligation or request scope")
        for request in data["requests"]:
            if not isinstance(request, dict) or set(request) != {"obligation_id", "artifact_id", "start_line", "end_line"}:
                raise ContractError("invalid evidence request")
            if request["obligation_id"] not in ids:
                raise ContractError("evidence request outside scope")
            positive_int(request["start_line"], "start_line")
            positive_int(request["end_line"], "end_line")
            if not isinstance(request["artifact_id"], str):
                raise ContractError("invalid artifact id")
        canonical(data)
        return data

    def _request_evidence(self, provider, request):
        node_id, artifact_id = request["obligation_id"], request["artifact_id"]
        if node_id in self.accepted:
            return
        o = self.task.by_id[node_id]
        start, end = request["start_line"], request["end_line"]
        if self.mode == "no_pull":
            code = "evidence_pull_disabled"
        elif artifact_id not in o.evidence:
            code = "undeclared_evidence"
        elif provider.placement == "remote" and not self.task.artifacts[artifact_id].cloud:
            code = "private_evidence"
        elif end < start or end - start + 1 > self.limits.max_requested_lines:
            code = "evidence_window_limit"
        elif end > len(self.task.artifacts[artifact_id].lines):
            code = "evidence_window_out_of_range"
        else:
            key = (provider.name, node_id, artifact_id)
            old = self.windows.get(key, [])
            merged = self._merge([*old, (start, end)])
            if merged == old:
                code = "evidence_already_supplied"
            else:
                self.windows[key] = merged
                self.ledger.add("evidence_requested", **request,
                                artifact_sha256=self.task.artifacts[artifact_id].sha256)
                return
        self._failure(node_id, code, "Choose a permitted, unseen evidence interval within the request limits.")
        self.ledger.add("evidence_denied", obligation_id=node_id, code=code)
