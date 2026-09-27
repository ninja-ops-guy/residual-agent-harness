"""Inference runtime: backend-agnostic model loading and generation.

Callers should only need `load_backend`, `DecodingConfig` and the
`Backend` protocol from this package.
"""

from .backend import (
    Backend,
    BackendCapabilities,
    DecodingConfig,
    load_backend,
    load_manifest,
    sample_next_token,
)

__all__ = [
    "Backend",
    "BackendCapabilities",
    "DecodingConfig",
    "load_backend",
    "load_manifest",
    "sample_next_token",
]
