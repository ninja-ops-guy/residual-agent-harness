"""OpenClaw Gateway execution-engine adapter.

OpenClaw is an execution substrate. Residual remains authoritative for policy,
verification, evidence, receipts, brakes, and HITL.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..core import ContractError
from .protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec

Transport = Callable[[str, Mapping[str, Any], Mapping[str, str], float], Any]


def _default_transport(
    endpoint: str,
    body: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout_s: float,
) -> Any:
    request = Request(
        endpoint,
        data=json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    with urlopen(request, timeout=timeout_s) as response:  # noqa: S310 - configured endpoint is intentional
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class OpenClawConfig:
    model: str
    gateway_url: str = "http://127.0.0.1:18789"
    timeout_s: float = 300.0
    capabilities: tuple[str, ...] = ("agent",)
    locality: str = "local"
    token: str | None = None
    token_env: str = "OPENCLAW_GATEWAY_TOKEN"
    openclaw_version: str = "unknown"

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ContractError("OpenClaw model is required")
        parsed = urlparse(self.gateway_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ContractError("OpenClaw gateway_url must be an absolute http(s) URL")
        if self.timeout_s <= 0:
            raise ContractError("OpenClaw timeout_s must be positive")
        if not self.capabilities or any(not isinstance(c, str) or not c.strip() for c in self.capabilities):
            raise ContractError("OpenClaw capabilities must contain non-empty strings")
        if self.locality not in {"local", "cloud", "hybrid"}:
            raise ContractError("OpenClaw locality must be local, cloud, or hybrid")


class OpenClawEngine:
    name = "openclaw"
    capability_class = "agent_runtime"

    def __init__(self, config: OpenClawConfig, *, transport: Transport | None = None) -> None:
        self.config = config
        self.version = config.openclaw_version
        self.locality = config.locality
        self._capabilities = frozenset(config.capabilities)
        self._transport = transport or _default_transport
        self._injected_transport = transport is not None

    def supports(self, capability: str) -> bool:
        return capability in self._capabilities

    def health(self) -> EngineHealth:
        """Return static readiness only; health checks must not hide network I/O."""
        if not self.config.model.strip():
            return EngineHealth.UNAVAILABLE
        parsed = urlparse(self.config.gateway_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return EngineHealth.UNAVAILABLE
        if self._injected_transport or self._resolved_token() is not None:
            return EngineHealth.HEALTHY
        # Trusted-proxy/no-bearer deployments may still be valid, but readiness
        # cannot be proven locally without performing network I/O.
        return EngineHealth.DEGRADED

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        endpoint = self.config.gateway_url.rstrip("/") + "/v1/responses"
        body = self._request_body(task, context)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        token = self._resolved_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        started = time.monotonic()
        raw = self._transport(endpoint, body, headers, self.config.timeout_s)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        normalized = self._normalize(raw, task=task)
        return EngineResult(
            candidate=normalized.candidate,
            tool_calls=normalized.tool_calls,
            token_usage=normalized.token_usage,
            wall_clock_ms=elapsed_ms,
            engine_trace=normalized.engine_trace,
            raw_metadata=normalized.raw_metadata,
        )

    def normalize(self, raw_output: Any) -> EngineResult:
        return self._normalize(raw_output, task=None)

    def _request_body(self, task: TaskSpec, context: ContextAssembly) -> dict[str, Any]:
        instructions = task.metadata.get("instructions") if isinstance(task.metadata, Mapping) else None
        labelled_input = {
            "task_id": task.task_id,
            "task": task.input,
            "context": dict(context.values),
        }
        body: dict[str, Any] = {
            "model": self.config.model,
            "input": json.dumps(labelled_input, sort_keys=True, separators=(",", ":"), default=str),
        }
        if isinstance(instructions, str) and instructions.strip():
            body["instructions"] = instructions
        return body

    def _normalize(self, raw_output: Any, *, task: TaskSpec | None) -> EngineResult:
        if not isinstance(raw_output, Mapping):
            return EngineResult(
                candidate=raw_output,
                raw_metadata=self._metadata(raw_output, observed_runtime=None, requested_runtime=self._requested_runtime(task)),
            )

        tool_calls = tuple(self._extract_tool_calls(raw_output))
        self._enforce_tool_boundary(task, tool_calls)
        observed_runtime = self._observed_runtime(raw_output)
        requested_runtime = self._requested_runtime(task)
        token_usage = self._token_usage(raw_output.get("usage"))
        candidate = self._candidate(raw_output)
        trace = self._trace(raw_output)

        return EngineResult(
            candidate=candidate,
            tool_calls=tool_calls,
            token_usage=token_usage,
            engine_trace=trace,
            raw_metadata=self._metadata(
                raw_output,
                observed_runtime=observed_runtime,
                requested_runtime=requested_runtime,
            ),
        )

    def _metadata(
        self,
        raw_output: Any,
        *,
        observed_runtime: str | None,
        requested_runtime: str | None,
    ) -> dict[str, Any]:
        runtime_verified: bool | None
        if observed_runtime is None:
            runtime_verified = None
        elif requested_runtime is None:
            runtime_verified = True
        else:
            runtime_verified = observed_runtime == requested_runtime
        return {
            "adapter": self.name,
            "gateway_origin": self._gateway_origin(),
            "model": self.config.model,
            "openclaw_runtime": observed_runtime,
            "requested_openclaw_runtime": requested_runtime,
            "runtime_identity_verified": runtime_verified,
            "residual_policy_authoritative": True,
            "response_id": raw_output.get("id") if isinstance(raw_output, Mapping) else None,
        }

    def _gateway_origin(self) -> str:
        parsed = urlparse(self.config.gateway_url)
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.scheme}://{host}{port}"

    def _resolved_token(self) -> str | None:
        if self.config.token:
            return self.config.token
        value = os.environ.get(self.config.token_env)
        return value if value else None

    @staticmethod
    def _candidate(raw: Mapping[str, Any]) -> Any:
        output_text = raw.get("output_text")
        if isinstance(output_text, str):
            return output_text

        output = raw.get("output")
        if isinstance(output, list):
            pieces: list[str] = []
            for item in output:
                if not isinstance(item, Mapping):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for part in content:
                        if not isinstance(part, Mapping):
                            continue
                        text = part.get("text") or part.get("output_text")
                        if isinstance(text, str):
                            pieces.append(text)
            if pieces:
                return "".join(pieces)

        choices = raw.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, Mapping):
                message = first.get("message")
                if isinstance(message, Mapping) and "content" in message:
                    return message.get("content")
                if "text" in first:
                    return first.get("text")

        if "candidate" in raw:
            return raw.get("candidate")
        return raw

    @classmethod
    def _extract_tool_calls(cls, raw: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        output = raw.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, Mapping):
                    continue
                kind = str(item.get("type", ""))
                if kind in {"function_call", "tool_call"}:
                    name = item.get("name")
                    if not name and isinstance(item.get("function"), Mapping):
                        name = item["function"].get("name")
                    yield {"name": name, "type": kind, "call_id": item.get("call_id") or item.get("id")}

        choices = raw.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, Mapping):
                    continue
                message = choice.get("message")
                if not isinstance(message, Mapping):
                    continue
                calls = message.get("tool_calls")
                if not isinstance(calls, list):
                    continue
                for call in calls:
                    if not isinstance(call, Mapping):
                        continue
                    function = call.get("function")
                    name = function.get("name") if isinstance(function, Mapping) else call.get("name")
                    yield {"name": name, "type": call.get("type") or "tool_call", "call_id": call.get("id")}

    @staticmethod
    def _token_usage(usage: Any) -> int | None:
        if not isinstance(usage, Mapping):
            return None
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if isinstance(input_tokens, int) or isinstance(output_tokens, int):
            return int(input_tokens or 0) + int(output_tokens or 0)
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if isinstance(prompt_tokens, int) or isinstance(completion_tokens, int):
            return int(prompt_tokens or 0) + int(completion_tokens or 0)
        return None

    @staticmethod
    def _trace(raw: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
        output = raw.get("output")
        if not isinstance(output, list):
            return ()
        trace: list[Mapping[str, Any]] = []
        for item in output:
            if isinstance(item, Mapping):
                trace.append({"id": item.get("id"), "type": item.get("type")})
        return tuple(trace)

    @staticmethod
    def _requested_runtime(task: TaskSpec | None) -> str | None:
        if task is None or not isinstance(task.metadata, Mapping):
            return None
        value = task.metadata.get("openclaw_runtime_id")
        return value if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _observed_runtime(raw: Mapping[str, Any]) -> str | None:
        for key in ("agentHarnessId", "agent_harness_id", "runtime_id", "agentRuntimeId"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value
        metadata = raw.get("metadata")
        if isinstance(metadata, Mapping):
            for key in ("agentHarnessId", "agent_harness_id", "runtime_id", "agentRuntimeId"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return None

    @classmethod
    def _allowed_tools(cls, task: TaskSpec | None) -> frozenset[str] | None:
        if task is None or not isinstance(task.metadata, Mapping):
            return None
        raw = task.metadata.get("allowed_tools")
        if raw is None:
            contract = task.metadata.get("worker_contract")
            if isinstance(contract, Mapping):
                raw = contract.get("allowed_tools")
        if raw is None:
            return None
        if isinstance(raw, str):
            raw = (raw,)
        try:
            names = frozenset(str(name) for name in raw)
        except TypeError as exc:
            raise ContractError("allowed_tools must be an iterable of tool names") from exc
        if any(not name for name in names):
            raise ContractError("allowed_tools cannot contain empty names")
        return names

    @classmethod
    def _enforce_tool_boundary(
        cls,
        task: TaskSpec | None,
        tool_calls: tuple[Mapping[str, Any], ...],
    ) -> None:
        allowed = cls._allowed_tools(task)
        if allowed is None:
            return
        for call in tool_calls:
            name = call.get("name")
            if not isinstance(name, str) or name not in allowed:
                raise ContractError(f"OpenClaw observed forbidden tool invocation: {name!r}")
