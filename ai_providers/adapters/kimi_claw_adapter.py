"""Kimi Claw / OpenClaw gateway adapter."""
from urllib.parse import urlsplit

from ._http import validate_url
from .openai_adapter import OpenAICompatibleAdapter
from ..core import ProviderError


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

    def supports_tools(self, model):
        return isinstance(model, str) and model.startswith("openclaw/")
