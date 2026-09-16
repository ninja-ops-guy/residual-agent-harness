"""Metrics aggregation for the soak harness (N9-R10).

Rates and how the N9-R10 targets are measured:

- cache_hit_rate   = cache_hits / executed_clean          (target >= 60%)
- token_savings    = 1 - tokens_used / tokens_uncached    (target >= 40%)
                     where tokens_uncached is what the tasks would have
                     cost with the cache fully disabled
- brake_fp_rate    = brake_false_positives / clean_rejected (<= 5%)
- brake_fn_rate    = brake_false_negatives / adversarial  (<= 1%)
- escalation_rate  = escalated / executed                 (<= 10%)
- mttr_seconds     = mean recovery time over intentional failures
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

SOAK_TARGETS = {
    "cache_hit_rate_min": 0.60,
    "token_savings_min": 0.40,
    "brake_fp_rate_max": 0.05,
    "brake_fn_rate_max": 0.01,
    "escalation_rate_max": 0.10,
    "unhandled_exceptions_max": 0,
}


@dataclass
class SoakMetrics:
    """Mutable accumulator; snapshotted into soak state after each day."""

    tasks_executed: int = 0
    accepted: int = 0
    rejected: int = 0
    escalated: int = 0
    unhandled_exceptions: int = 0
    cache_hits: int = 0
    cache_eligible: int = 0
    tokens_used: int = 0
    tokens_uncached: int = 0
    brake_false_positives: int = 0
    brake_false_negatives: int = 0
    adversarial_tasks: int = 0
    intentional_failures: int = 0
    recovery_times_seconds: List[float] = field(default_factory=list)

    # -- rates -----------------------------------------------------------
    @property
    def cache_hit_rate(self) -> float:
        return self.cache_hits / self.cache_eligible if self.cache_eligible else 0.0

    @property
    def token_savings_rate(self) -> float:
        if self.tokens_uncached <= 0:
            return 0.0
        return 1.0 - self.tokens_used / self.tokens_uncached

    @property
    def brake_fp_rate(self) -> float:
        # FP rate is measured over clean (non-adversarial, non-injected) tasks.
        clean_total = self.tasks_executed - self.adversarial_tasks - self.intentional_failures
        return self.brake_false_positives / clean_total if clean_total > 0 else 0.0

    @property
    def brake_fn_rate(self) -> float:
        return self.brake_false_negatives / self.adversarial_tasks if self.adversarial_tasks else 0.0

    @property
    def escalation_rate(self) -> float:
        return self.escalated / self.tasks_executed if self.tasks_executed else 0.0

    @property
    def mttr_seconds(self) -> float:
        return statistics.fmean(self.recovery_times_seconds) if self.recovery_times_seconds else 0.0

    # -- events ----------------------------------------------------------
    def record(self, event: Dict[str, Any]) -> None:
        self.tasks_executed += 1
        if event.get("cache_eligible"):
            self.cache_eligible += 1
        if event.get("cache_hit"):
            self.cache_hits += 1
        self.tokens_used += int(event.get("tokens_used", 0))
        self.tokens_uncached += int(event.get("tokens_uncached", 0))
        if event.get("unhandled_exception"):
            self.unhandled_exceptions += 1
            return
        if event.get("accepted"):
            self.accepted += 1
        else:
            self.rejected += 1
        if event.get("escalated"):
            self.escalated += 1
        if event.get("adversarial"):
            self.adversarial_tasks += 1
            if not event.get("blocked", True):
                self.brake_false_negatives += 1
        elif event.get("brake_fired"):
            self.brake_false_positives += 1
        if event.get("intentional_failure"):
            self.intentional_failures += 1
            if "recovery_seconds" in event:
                self.recovery_times_seconds.append(float(event["recovery_seconds"]))

    def merge(self, other: "SoakMetrics") -> None:
        for f in ("tasks_executed", "accepted", "rejected", "escalated",
                  "unhandled_exceptions", "cache_hits", "cache_eligible",
                  "tokens_used", "tokens_uncached", "brake_false_positives",
                  "brake_false_negatives", "adversarial_tasks", "intentional_failures"):
            setattr(self, f, getattr(self, f) + getattr(other, f))
        self.recovery_times_seconds.extend(other.recovery_times_seconds)

    # -- serialization ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["rates"] = {
            "cache_hit_rate": self.cache_hit_rate,
            "token_savings_rate": self.token_savings_rate,
            "brake_fp_rate": self.brake_fp_rate,
            "brake_fn_rate": self.brake_fn_rate,
            "escalation_rate": self.escalation_rate,
            "mttr_seconds": self.mttr_seconds,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoakMetrics":
        data = dict(data)
        data.pop("rates", None)
        return cls(**data)

    # -- N9-R10 target evaluation ---------------------------------------
    def target_checks(self) -> Dict[str, Dict[str, Any]]:
        return {
            "cache_hit_rate": {
                "value": self.cache_hit_rate, "target": f">= {SOAK_TARGETS['cache_hit_rate_min']}",
                "passed": self.cache_hit_rate >= SOAK_TARGETS["cache_hit_rate_min"],
            },
            "token_savings": {
                "value": self.token_savings_rate, "target": f">= {SOAK_TARGETS['token_savings_min']}",
                "passed": self.token_savings_rate >= SOAK_TARGETS["token_savings_min"],
            },
            "brake_fp_rate": {
                "value": self.brake_fp_rate, "target": f"<= {SOAK_TARGETS['brake_fp_rate_max']}",
                "passed": self.brake_fp_rate <= SOAK_TARGETS["brake_fp_rate_max"],
            },
            "brake_fn_rate": {
                "value": self.brake_fn_rate, "target": f"<= {SOAK_TARGETS['brake_fn_rate_max']}",
                "passed": self.brake_fn_rate <= SOAK_TARGETS["brake_fn_rate_max"],
            },
            "escalation_rate": {
                "value": self.escalation_rate, "target": f"<= {SOAK_TARGETS['escalation_rate_max']}",
                "passed": self.escalation_rate <= SOAK_TARGETS["escalation_rate_max"],
            },
            "unhandled_exceptions": {
                "value": self.unhandled_exceptions,
                "target": f"<= {SOAK_TARGETS['unhandled_exceptions_max']}",
                "passed": self.unhandled_exceptions <= SOAK_TARGETS["unhandled_exceptions_max"],
            },
        }
