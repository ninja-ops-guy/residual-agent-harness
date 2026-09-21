"""StationLM provider stub: advisory decision models for RESIDUAL Station.

Invariant: the model proposes; the Station decides. Everything in this
package is advisory-only and fail-closed. RESIDUAL remains authoritative for
policy, authority, contracts, evidence, verification, brakes, quarantine,
budgets, escalation, and qualification.
"""
from .decision_model import (
    DECISION_SCHEMA_VERSION, DecisionModel, DecisionProposal, DecisionRequest,
    FakeDecisionModel, default_policy, validate_proposal,
)
from .model_registry import ModelManifest, ModelRegistry, RegistryEntry
from .provider import AdvisoryResult, DecisionReceipt, StationLMProvider
from .rollback import RollbackMonitor, RollbackTrigger
from .shadow import PairedDecision, ShadowModeHook
from .canary import CANARY_SCHEMA, DEFAULT_STEPS, CanaryRollout
from .integration import FALLBACK_SCHEMA, StationShadowIntegration

__all__ = [
    "DECISION_SCHEMA_VERSION", "DecisionModel", "DecisionProposal",
    "DecisionRequest", "FakeDecisionModel", "default_policy", "validate_proposal",
    "ModelManifest", "ModelRegistry", "RegistryEntry",
    "AdvisoryResult", "DecisionReceipt", "StationLMProvider",
    "RollbackMonitor", "RollbackTrigger", "PairedDecision", "ShadowModeHook",
    "CANARY_SCHEMA", "DEFAULT_STEPS", "CanaryRollout",
    "FALLBACK_SCHEMA", "StationShadowIntegration",
]
