"""RESIDUAL: verifiable task boundaries for hybrid agents."""

from .goalspec import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
from .verifier import CheckResult, CriterionResult, VerificationReport, Verifier
from .brakes import (
    Brake, BrakeAction, BrakeTrip, BudgetBrake, CompletionBrake,
    MaxIterationBrake, NoProgressBrake, build_brakes,
)
from .quarantine import (
    ActionType, DeniedAction, ExecutedAction, HeldAction, Policy, PolicyDecision,
    ProposedAction, QuarantineStore, budget_policy, denylist_policy,
    path_traversal_policy,
)
from .loop import HarnessPass, LoopController, RunOutcome, RunResult
from .integration import QuarantinedProvider, default_policies

__version__ = "0.3.0"

__all__ = [
    "AmendmentRule", "CheckType", "GoalSpec", "SuccessCriterion",
    "CheckResult", "CriterionResult", "VerificationReport", "Verifier",
    "Brake", "BrakeAction", "BrakeTrip",
    "BudgetBrake", "CompletionBrake", "MaxIterationBrake", "NoProgressBrake",
    "build_brakes",
    "ActionType", "DeniedAction", "ExecutedAction", "HeldAction", "Policy", "PolicyDecision",
    "ProposedAction", "QuarantineStore",
    "budget_policy", "denylist_policy", "path_traversal_policy",
    "HarnessPass", "LoopController", "RunOutcome", "RunResult",
    "QuarantinedProvider", "default_policies",
]
