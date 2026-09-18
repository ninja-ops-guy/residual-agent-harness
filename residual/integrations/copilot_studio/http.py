"""Framework-neutral HTTP adapter matching the Copilot Studio OpenAPI surface."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ...core import ContractError, strict_json
from .contracts import CopilotAPIError, external_id
from .service import CopilotStudioService


_MISSION_PATH = re.compile(r"^/v1/copilot/missions/([A-Za-z0-9][A-Za-z0-9._:-]{0,127})$")
_EVIDENCE_PATH = re.compile(r"^/v1/copilot/missions/([A-Za-z0-9][A-Za-z0-9._:-]{0,127})/evidence$")
_CANCEL_PATH = re.compile(r"^/v1/copilot/missions/([A-Za-z0-9][A-Za-z0-9._:-]{0,127})/cancel$")
MAX_HTTP_BODY = 320 * 1024


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    body: dict[str, Any]


class CopilotHTTPAdapter:
    def __init__(self, service: CopilotStudioService):
        if not isinstance(service, CopilotStudioService):
            raise ContractError("CopilotHTTPAdapter requires a CopilotStudioService")
        self.service = service

    @staticmethod
    def _bearer(headers: dict[str, str]) -> str:
        normalized = {str(k).lower(): v for k, v in (headers or {}).items()}
        value = normalized.get("authorization")
        if not isinstance(value, str):
            raise CopilotAPIError(401, "authentication_failed", "authentication is required")
        parts = value.strip().split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
            raise CopilotAPIError(401, "authentication_failed", "authentication is required")
        return parts[1]

    @staticmethod
    def _json_body(body: bytes | str | None) -> Any:
        if body is None:
            raise CopilotAPIError(400, "invalid_request", "request body is required")
        raw = body.encode("utf-8") if isinstance(body, str) else body
        if not isinstance(raw, bytes):
            raise CopilotAPIError(400, "invalid_request", "request body must be UTF-8 JSON")
        if len(raw) > MAX_HTTP_BODY:
            raise CopilotAPIError(413, "request_too_large", "request body exceeds the supported size")
        try:
            text = raw.decode("utf-8")
            return strict_json(text)
        except (UnicodeDecodeError, ValueError, TypeError):
            raise CopilotAPIError(400, "invalid_json", "request body must be valid JSON") from None

    def dispatch(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | str | None = None,
        now: int,
    ) -> HTTPResponse:
        request_id = None
        try:
            token = self._bearer(headers or {})
            verb = method.upper()
            if verb == "POST" and path == "/v1/copilot/missions":
                payload = self._json_body(body)
                if isinstance(payload, dict) and isinstance(payload.get("request_id"), str):
                    try:
                        request_id = external_id(payload["request_id"], "request_id")
                    except CopilotAPIError:
                        request_id = None
                return HTTPResponse(202, self.service.submit(token, payload, now=now))

            match = _MISSION_PATH.fullmatch(path)
            if verb == "GET" and match:
                return HTTPResponse(200, self.service.get(token, match.group(1), now=now))

            match = _EVIDENCE_PATH.fullmatch(path)
            if verb == "GET" and match:
                return HTTPResponse(200, self.service.evidence(token, match.group(1), now=now))

            match = _CANCEL_PATH.fullmatch(path)
            if verb == "POST" and match:
                return HTTPResponse(202, self.service.cancel(token, match.group(1), now=now))

            raise CopilotAPIError(404, "route_not_found", "route was not found")
        except CopilotAPIError as exc:
            return HTTPResponse(exc.status, exc.to_dict(request_id))
        except Exception:
            # Deliberately no exception string, provider detail, token, or stack trace.
            return HTTPResponse(500, {
                "code": "internal_error",
                "message": "the request could not be completed",
                "request_id": request_id,
            })
