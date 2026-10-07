"""Commercial licensing, support SLAs, pilot programs, and training tracking.

Implements the code portions of SPEC-ENT-007 (Change Management and
Governance) and SPEC-ENT-008 (Commercial and Legal Framework).
"""
from __future__ import annotations

from .model import (COMMERCIAL_FEATURES, OPEN_FEATURES, License, MeteringModel,
                    Tier, UsageMeter)
from .pilot import (GraduationEvaluation, MetricResult, PilotPlan,
                    MAX_DURATION_DAYS, MIN_DURATION_DAYS)
from .support import (Channel, Severity, SlaTracker, SupportCase, SupportTier,
                      RESPONSE_SLA_SECONDS)
from .training import REQUIRED_EXERCISES, Role, TrainingRecord

__all__ = [
    "Channel", "COMMERCIAL_FEATURES", "GraduationEvaluation", "License",
    "MAX_DURATION_DAYS", "MeteringModel", "MetricResult", "MIN_DURATION_DAYS",
    "OPEN_FEATURES", "PilotPlan", "REQUIRED_EXERCISES",
    "RESPONSE_SLA_SECONDS", "Role", "Severity", "SlaTracker", "SupportCase",
    "SupportTier", "Tier", "TrainingRecord", "UsageMeter",
]
