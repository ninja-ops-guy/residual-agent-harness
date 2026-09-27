"""Import shim for the model scaffold.

The scaffold lives at `research/slm/scaffold/` on branch
`slm-infra/training-env`. In the repo checkout it is importable as
`research.slm.scaffold` (namespace packages); in the inference container
it is copied to `/app/scaffold` and importable as `scaffold`.
"""

from __future__ import annotations

try:  # repo checkout layout
    from research.slm.scaffold.config import ModelConfig
    from research.slm.scaffold.model import NanoLM
except ImportError:  # container layout (Dockerfile.inference)
    from scaffold.config import ModelConfig  # type: ignore[no-redef]
    from scaffold.model import NanoLM  # type: ignore[no-redef]

__all__ = ["ModelConfig", "NanoLM"]
