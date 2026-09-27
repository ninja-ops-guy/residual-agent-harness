"""Moonshot AI / Kimi OpenAI-compatible adapter."""
from urllib.parse import urlsplit

from ._http import validate_url
from .openai_adapter import OpenAICompatibleAdapter
from ..core import ProviderError


def _moonshot_base_url(base_url: str) -> str:
    """Bind Moonshot credentials to the real Moonshot API origin.

    A caller that needs a proxy or alternate OpenAI-compatible endpoint must
    use the generic openai_compatible provider identity instead of retaining
    the stronger "moonshot" attribution.
    """
    base = validate_url(base_url, "moonshot")
    try:
        parsed = urlsplit(base)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.moonshot.ai"
            or parsed.port not in (None, 443)
            or parsed.path.rstrip("/") != "/v1"
        ):
            raise ValueError
    except (ValueError, TypeError):
        raise ProviderError(provider="moonshot", code="config") from None
    return base


class MoonshotAdapter(OpenAICompatibleAdapter):
    """Direct Moonshot API adapter with origin-bound credentials."""

    name = "moonshot"

    def __init__(
        self,
        api_key=None,
        base_url="https://api.moonshot.ai/v1",
        timeout=120.0,
        output_token_field="max_tokens",
    ):
        super().__init__(
            api_key=api_key,
            base_url=_moonshot_base_url(base_url),
            timeout=timeout,
            output_token_field=output_token_field,
        )

    def supports_tools(self, model):
        return isinstance(model, str) and model.startswith("kimi-")
