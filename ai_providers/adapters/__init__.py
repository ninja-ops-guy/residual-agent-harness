"""Provider adapters. Each module exports one Provider implementation."""

from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .google_adapter import GoogleAdapter
from .azure_adapter import AzureAdapter
from .bedrock_adapter import BedrockAdapter
from .ollama_adapter import OllamaAdapter
from .moonshot_adapter import MoonshotAdapter
from .kimi_claw_adapter import KimiClawAdapter

__all__ = [
    "OpenAIAdapter", "AnthropicAdapter", "GoogleAdapter",
    "AzureAdapter", "BedrockAdapter", "OllamaAdapter",
    "MoonshotAdapter", "KimiClawAdapter",
]
