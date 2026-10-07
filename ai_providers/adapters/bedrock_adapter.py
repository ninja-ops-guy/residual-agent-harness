"""
ai_providers.adapters.bedrock_adapter
=====================================
AWS Bedrock (Converse API). Uses SigV4 request signing. Supports any
Bedrock model via the unified Converse interface (Claude, Llama, Mistral,
Command, Titan...).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterator, Optional

from ..core import (
    ChatRequest, ChatResponse, Message, Provider, ProviderError,
    Role, StreamChunk, ToolCall, ToolSpec,
)
from ._http import HTTPAdapter, usage_values, cached_usage, finish, validate_url, encode
from urllib.parse import quote, urlsplit
import re


class BedrockAdapter(HTTPAdapter):
    supports_streaming = False
    name = "bedrock"
    SERVICE = "bedrock"
    HOST_TEMPLATE = "bedrock-runtime.{region}.amazonaws.com"

    def __init__(self, access_key: Optional[str] = None, secret_key: Optional[str] = None,
                 region: str = "us-east-1", session_token: Optional[str] = None, timeout: float = 120.0, base_url: Optional[str] = None):
        self.access_key = access_key
        self.secret_key = secret_key
        if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region): raise ProviderError(provider=self.name, code="config")
        self.region = region
        self.session_token = session_token
        self.timeout = timeout
        self.base_url = validate_url(base_url or "https://" + self.HOST_TEMPLATE.format(region=region), self.name)

    def _host(self) -> str:
        return urlsplit(self.base_url).netloc

    def _url(self, model: str) -> str:
        return self.base_url + "/model/" + quote(model, safe="") + "/converse"

    # -- SigV4 signing --------------------------------------------------------

    def _sign(self, method: str, url_path: str, query: str, headers: dict[str, str], body: bytes) -> dict[str, str]:
        """Minimal SigV4 implementation. Works everywhere; swap for boto3 if preferred."""
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        if not self.access_key or not self.secret_key:
            from ..core import AuthenticationError
            raise AuthenticationError(provider=self.name, code="authentication")
        headers = {k.lower(): " ".join(v.split()) for k, v in headers.items()}
        headers["host"] = self._host()
        headers["x-amz-date"] = amz_date
        if self.session_token:
            headers["x-amz-security-token"] = self.session_token

        canonical_headers = "".join(f"{k.lower()}:{headers[k].strip()}\n" for k in sorted(headers))
        signed_headers = ";".join(sorted(headers))
        payload_hash = hashlib.sha256(body).hexdigest()

        canonical_request = "\n".join([
            method, quote(url_path, safe="/~"), query,
            canonical_headers, signed_headers, payload_hash,
        ])

        credential_scope = f"{date_stamp}/{self.region}/{self.SERVICE}/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256", amz_date, credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ])

        def _sig(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()

        k_date = _sig(("AWS4" + (self.secret_key or "")).encode(), date_stamp)
        k_region = _sig(k_date, self.region)
        k_service = _sig(k_region, self.SERVICE)
        k_signing = _sig(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

        headers["Authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return headers

    # -- translation ----------------------------------------------------------

    @staticmethod
    def _msg_to_bedrock(m: Message) -> dict[str, Any]:
        if m.role == Role.SYSTEM:
            return {"role": "system", "content": [{"text": m.content}]}
        role = "assistant" if m.role == Role.ASSISTANT else "user"
        if m.role == Role.TOOL:
            return {"role": "user", "content": [{"toolResult": {
                "toolUseId": m.tool_call_id,
                "content": [{"text": m.content}],
            }}]}
        blocks = ([{"text": m.content}] if m.content else []) + [{"toolUse": {"toolUseId": t.id, "name": t.name, "input": json.loads(t.arguments)}} for t in m.tool_calls]
        return {"role": role, "content": blocks}

    @staticmethod
    def _tool_to_bedrock(t: ToolSpec) -> dict[str, Any]:
        return {"toolSpec": {"name": t.name, "description": t.description, "inputSchema": {"json": t.parameters}}}

    def _build_body(self, req: ChatRequest, stream: bool = False) -> dict[str, Any]:
        system = [self._msg_to_bedrock(m) for m in req.messages if m.role == Role.SYSTEM]
        messages = [self._msg_to_bedrock(m) for m in req.messages if m.role != Role.SYSTEM]
        body: dict[str, Any] = {"messages": messages}
        if system:
            body["system"] = [c for msg in system for c in msg["content"]]
        if req.response_schema is not None:
            body.setdefault("system", []).append({"text": "Return only JSON matching: " + encode(req.response_schema).decode()})
        if req.tools:
            body["toolConfig"] = {"tools": [self._tool_to_bedrock(t) for t in req.tools]}
        inf: dict[str, Any] = {}
        if req.temperature is not None:
            inf["temperature"] = req.temperature
        if req.max_tokens is not None:
            inf["maxTokens"] = req.max_tokens
        if req.stop:
            inf["stopSequences"] = list(req.stop)
        if inf:
            body["inferenceConfig"] = inf
        return self._options(req, body)

    @staticmethod
    def _parse_response(data: dict[str, Any], model: str) -> ChatResponse:
        output = data["output"]
        msg = output["message"]
        text_parts, tool_calls = [], []
        for block in msg.get("content", []):
            if "text" in block:
                text_parts.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append(ToolCall(id=tu.get("toolUseId", ""), name=tu.get("name", ""),
                                           arguments=json.dumps(tu.get("input", {}))))
        stop = data.get("stopReason") or "end_turn"
        reason = finish(stop)
        return ChatResponse(
            model=model,
            content="".join(text_parts),
            tool_calls=tuple(tool_calls),
            finish_reason=reason,
            usage=cached_usage(data.get("usage") or {}, "inputTokens", "outputTokens", "cacheReadInputTokens", "cacheWriteInputTokens"),
            raw=data,
        )

    def _request_url(self, req, stream): return self._url(req.model)

    def _parse(self, data, model): return self._parse_response(data, model)

    def chat(self, req):
        body = self.wire_bytes(req)
        url = self._url(req.model)
        headers = self._sign("POST", urlsplit(url).path, "", {"content-type":"application/json"}, body)
        try:
            return self._parse_response(self._json(url, body, headers), req.model)
        except ProviderError: raise
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            raise ProviderError(provider=self.name, code="invalid_response") from None

    def list_models(self):
        # Discovery needs separate AWS catalog permissions and does not reveal inference-profile IDs.
        raise ProviderError(provider=self.name, code="not_implemented")

    def supports_tools(self, model):
        return model.startswith(("anthropic.claude", "meta.llama3", "mistral.mistral-large"))
