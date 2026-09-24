"""
ai_providers.core
==================
Provider-agnostic types. Every adapter — cloud or local — speaks these.
No provider-specific types leak above this layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import json
from typing import Any, AsyncIterator, Iterator, Optional, Protocol


class ProviderName(str, Enum):
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    BEDROCK = "bedrock"
    OLLAMA = "ollama"
    MOONSHOT = "moonshot"
    KIMI_CLAW = "kimi_claw"
    ROUTER = "router"


class ErrorCode(str, Enum):
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    MODEL_NOT_FOUND = "model_not_found"
    SERVER_ERROR = "server_error"
    HTTP_ERROR = "http_error"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    CONFIG = "config"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    RESPONSE_TOO_LARGE = "response_too_large"
    REDIRECT_REFUSED = "redirect_refused"
    NOT_IMPLEMENTED = "not_implemented"
    UNKNOWN_PROVIDER = "unknown_provider"
    EXHAUSTED = "exhausted"
    STREAM_INCOMPLETE = "stream_incomplete"
    CONTENT_FILTER = "content_filter"


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class Message:
    role: Role
    content: str
    name: Optional[str] = None          # for tool messages
    tool_call_id: Optional[str] = None  # for tool result messages
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_calls: tuple["ToolCall", ...] = ()

    def __post_init__(self):
        try: object.__setattr__(self, "role", Role(self.role))
        except ValueError: raise ValueError("Unknown message role") from None
        if not isinstance(self.content, str): raise ValueError("Message content must be text")
        if self.role == Role.TOOL and not self.tool_call_id: raise ValueError("Tool results require tool_call_id")


@dataclass(frozen=True)
class ToolSpec:
    """OpenAI-compatible tool schema. Adapters translate to native formats."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass(frozen=True)
class ChatRequest:
    model: str
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...] = ()
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stop: Optional[tuple[str, ...]] = None
    seed: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)  # adapter-specific, allowlisted options
    response_schema: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if not isinstance(self.model, str) or len(self.model) > 500: raise ValueError("Invalid model")
        if not self.messages or not all(isinstance(m, Message) for m in self.messages): raise ValueError("Messages are required")
        if self.max_tokens is not None and (type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 1000000): raise ValueError("Invalid output limit")
        if self.temperature is not None and (type(self.temperature) not in (int, float) or not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2): raise ValueError("Invalid temperature")
        if not isinstance(self.extra, dict): raise ValueError("extra must be an object")
        if self.response_schema is not None and not isinstance(self.response_schema, dict): raise ValueError("Invalid response schema")
        json.dumps(self.extra, allow_nan=False)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON string; caller parses

    def __post_init__(self):
        if not all(isinstance(v, str) for v in (self.id, self.name, self.arguments)):
            raise ValueError("Tool call fields must be strings")


@dataclass(frozen=True)
class ChatResponse:
    model: str
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = "stop"  # stop | length | tool_calls | error
    usage: dict[str, int] = field(default_factory=dict)  # {prompt_tokens, completion_tokens, total_tokens}
    raw: Any = None  # never emitted into telemetry
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.content, str) or not isinstance(self.model, str): raise ValueError("Invalid response content")
        if self.finish_reason not in {"stop", "length", "tool_calls", "content_filter", "error", "unknown"}: raise ValueError("Unknown finish reason")
        for value in self.usage.values():
            if type(value) is not int or value < 0: raise ValueError("Invalid token counter")

    def as_message(self):
        return Message(Role.ASSISTANT, self.content, metadata=self.metadata, tool_calls=self.tool_calls)


@dataclass(frozen=True)
class StreamChunk:
    """Normalized streaming delta. `content` may be partial text or None."""

    content: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    finish_reason: Optional[str] = None
    usage: dict[str, int] = field(default_factory=dict)


class ProviderError(Exception):
    """Base for all provider errors. Structured, never a bare string."""

    def __init__(self, message: str = "", *, provider: str = "router", code: Optional[str] = None,
                 retryable: bool = False, status: Optional[int] = None):
        # Never retain upstream error bodies, URL queries or credentials in errors.
        try: self.provider = ProviderName(provider).value
        except ValueError: self.provider = "router"
        self.code = ErrorCode(code or "invalid_response").value
        self.retryable, self.status = bool(retryable), status
        super().__init__(f"{self.provider}: {self.code}")

    def to_dict(self):
        return {"provider": self.provider, "code": self.code, "retryable": self.retryable,
                "status": self.status, "retry_after": getattr(self, "retry_after", None)}


class AuthenticationError(ProviderError):
    pass


class RateLimitError(ProviderError):
    def __init__(self, message: str, *, provider: str, retry_after: Optional[float] = None):
        super().__init__(message, provider=provider, code="rate_limit", retryable=True, status=429)
        self.retry_after = retry_after


class ModelNotFoundError(ProviderError):
    pass


class Provider(Protocol):
    """The contract every adapter implements."""

    name: str  # closed vocabulary: "openai", "anthropic", "ollama", ...

    def chat(self, req: ChatRequest) -> ChatResponse: ...
    def stream(self, req: ChatRequest) -> Iterator[StreamChunk]: ...
    async def achat(self, req: ChatRequest) -> ChatResponse: ...
    async def astream(self, req: ChatRequest) -> AsyncIterator[StreamChunk]: ...
    def list_models(self) -> list[str]: ...
    def supports_tools(self, model: str) -> bool: ...
