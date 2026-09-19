"""Kimi Claw / OpenClaw gateway adapter."""
import os
import re
from urllib.parse import urlsplit

from ._http import validate_url
from .openai_adapter import OpenAICompatibleAdapter
from ..core import ProviderError


GATEWAY_SECRET_ENV = ("KIMI_CLAW_TOKEN", "OPENCLAW_GATEWAY_TOKEN", "OPENCLAW_GATEWAY_PASSWORD")
_AGENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\\Z")


def resolve_kimi_claw_secret(explicit=None):
    """Resolve only gateway-specific secrets; never consume generic cloud LLM keys."""
    if explicit:
        return explicit
    for name in GATEWAY_SECRET_ENV:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _kimi_claw_agent_target(model: str) -> str:
    """Validate OpenClaw's agent-first model contract, not backend model ids."""
    if model in {"openclaw", "openclaw/default"}:
        return model
    for prefix in ("openclaw/", "openclaw:", "agent:"):
        if isinstance(model, str) and model.startswith(prefix):
            agent_id = model[len(prefix):]
            if _AGENT_ID.fullmatch(agent_id):
                return model
    raise ProviderError(provider="kimi_claw", code="invalid_request")


def _kimi_claw_base_url(base_url: str) -> str:
    """Require the operator-equivalent OpenClaw credential to stay loopback."""
    base = validate_url(base_url, "kimi_claw", local=True)
    try:
        parsed = urlsplit(base)
        if parsed.path.rstrip("/") != "/v1":
            raise ValueError
    except (ValueError, TypeError):
        raise ProviderError(provider="kimi_claw", code="config") from None
    return base


class KimiClawAdapter(OpenAICompatibleAdapter):
    """Run RESIDUAL work through a loopback Kimi Claw/OpenClaw gateway."""

    name = "kimi_claw"
    allowed_extra = OpenAICompatibleAdapter.allowed_extra | {"user"}

    def __init__(
        self,
        api_key=None,
        base_url="http://127.0.0.1:18789/v1",
        timeout=300.0,
        output_token_field="max_completion_tokens",
    ):
        super().__init__(
            api_key=api_key,
            base_url=_kimi_claw_base_url(base_url),
            timeout=timeout,
            output_token_field=output_token_field,
        )

    def _build_body(self, req, stream=False):
        _kimi_claw_agent_target(req.model)
        return super()._build_body(req, stream)

    def supports_tools(self, model):
        try:
            _kimi_claw_agent_target(model)
            return True
        except ProviderError:
            return False
