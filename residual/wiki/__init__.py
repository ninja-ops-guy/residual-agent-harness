"""RESIDUAL Wiki: documentation retrieval and bounded setup skills."""

from .agent import WikiAssistant
from .index import WikiDocument, WikiIndex, WikiSearchHit, resolve_docs_root
from .skills import SkillPlan, SkillRegistry, SkillSpec

__all__ = [
    "SkillPlan",
    "SkillRegistry",
    "SkillSpec",
    "WikiAssistant",
    "WikiDocument",
    "WikiIndex",
    "WikiSearchHit",
    "resolve_docs_root",
]
