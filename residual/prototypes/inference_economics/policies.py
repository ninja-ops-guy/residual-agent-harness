"""Deterministic development-only policy models required by IE-001 Q5-Q8.

These models operate solely on frozen inputs. They do not call providers,
spawn workers, mutate production scheduling state, verify candidates, issue
receipts, or integrate results.
"""

from collections import OrderedDict
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from math import sqrt
from typing import FrozenSet, Optional


# ---------------------------------------------------------------------------
# Q5 pressure/backpressure model


class AdmissionAction(str, Enum):
    ADMIT = "ADMIT"
    PAUSE = "PAUSE"
    CANCEL = "CANCEL"
    OVERLOAD = "OVERLOAD"


@dataclass(frozen=True)
class PressurePolicyConfig:
    max_global_in_flight: int = 4
    max_mission_in_flight: int = 2
    verifier_high: int = 4
    verifier_low: int = 2
    integration_high: int = 4
    integration_low: int = 2
    hard_queue_bound: int = 8

    def __post_init__(self) -> None:
        values = (
            self.max_global_in_flight,
            self.max_mission_in_flight,
            self.verifier_high,
            self.verifier_low,
            self.integration_high,
            self.integration_low,
            self.hard_queue_bound,
        )
        if min(values) < 0:
            raise ValueError("pressure limits must be non-negative")
        if self.verifier_low > self.verifier_high:
            raise ValueError("verifier low watermark cannot exceed high")
        if self.integration_low > self.integration_high:
            raise ValueError("integration low watermark cannot exceed high")
        if self.hard_queue_bound < max(self.verifier_high, self.integration_high):
            raise ValueError("hard queue bound must be >= high watermarks")


@dataclass(frozen=True)
class PressureInput:
    ready_frontier_depth: int
    global_in_flight: int
    mission_in_flight: int
    pending_verifications: int
    integration_queue_depth: int
    canceled: bool = False
    deadline_expired: bool = False
    previously_paused: bool = False

    def __post_init__(self) -> None:
        if min(
            self.ready_frontier_depth,
            self.global_in_flight,
            self.mission_in_flight,
            self.pending_verifications,
            self.integration_queue_depth,
        ) < 0:
            raise ValueError("pressure inputs cannot be negative")


@dataclass(frozen=True)
class AdmissionDecision:
    action: AdmissionAction
    reason: str
    dropped_work: int = 0


class PressurePolicy:
    """Frozen deterministic admission policy with hysteresis and no-drop output."""

    def __init__(self, config: PressurePolicyConfig):
        self.config = config

    def decide(self, state: PressureInput) -> AdmissionDecision:
        c = self.config
        if state.canceled or state.deadline_expired:
            return AdmissionDecision(AdmissionAction.CANCEL, "host_cancel_or_deadline")
        if (
            state.pending_verifications > c.hard_queue_bound
            or state.integration_queue_depth > c.hard_queue_bound
        ):
            # Explicit overload, never silent drop.
            return AdmissionDecision(AdmissionAction.OVERLOAD, "hard_queue_bound_exceeded", 0)
        if state.previously_paused:
            if (
                state.pending_verifications > c.verifier_low
                or state.integration_queue_depth > c.integration_low
            ):
                return AdmissionDecision(AdmissionAction.PAUSE, "hysteresis_drain")
        else:
            if state.pending_verifications >= c.verifier_high:
                return AdmissionDecision(AdmissionAction.PAUSE, "verifier_high_watermark")
            if state.integration_queue_depth >= c.integration_high:
                return AdmissionDecision(AdmissionAction.PAUSE, "integration_high_watermark")
        if state.global_in_flight >= c.max_global_in_flight:
            return AdmissionDecision(AdmissionAction.PAUSE, "global_in_flight_limit")
        if state.mission_in_flight >= c.max_mission_in_flight:
            return AdmissionDecision(AdmissionAction.PAUSE, "mission_in_flight_limit")
        if state.ready_frontier_depth <= 0:
            return AdmissionDecision(AdmissionAction.PAUSE, "nothing_ready")
        return AdmissionDecision(AdmissionAction.ADMIT, "within_bounds")


# ---------------------------------------------------------------------------
# Q6 provenance-safe cache model


class CacheLookupStatus(str, Enum):
    HIT = "HIT"
    MISS = "MISS"
    POLICY_BLOCK = "POLICY_BLOCK"
    TAMPERED = "TAMPERED"


@dataclass(frozen=True)
class ContextFragmentIdentity:
    schema_revision: str
    obligation_id: str
    contract_hash: str
    artifact_path: str
    artifact_content_hash: str
    window_start: int
    window_end: int
    dependency_receipt_hashes: tuple[str, ...]
    verifier_revision: str
    disclosure_class: str
    template_revision: str

    def __post_init__(self) -> None:
        if self.window_start < 0 or self.window_end < self.window_start:
            raise ValueError("invalid evidence window")
        if self.disclosure_class not in {"local_only", "remote"}:
            raise ValueError("unsupported disclosure class")
        required = (
            self.schema_revision,
            self.obligation_id,
            self.contract_hash,
            self.artifact_path,
            self.artifact_content_hash,
            self.verifier_revision,
            self.template_revision,
        )
        if any(not value for value in required):
            raise ValueError("cache identity fields cannot be empty")

    def canonical_key(self) -> str:
        encoded = json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ContextFragment:
    identity: ContextFragmentIdentity
    content: bytes
    content_hash: str
    requires_reverification: bool = True

    @staticmethod
    def create(identity: ContextFragmentIdentity, content: bytes) -> "ContextFragment":
        return ContextFragment(
            identity=identity,
            content=content,
            content_hash=hashlib.sha256(content).hexdigest(),
            requires_reverification=True,
        )


@dataclass(frozen=True)
class CacheLookup:
    status: CacheLookupStatus
    fragment: Optional[ContextFragment]
    reason: str


class ContextCacheModel:
    """Bounded deterministic FIFO semantic-fragment cache."""

    def __init__(self, capacity_items: int = 8):
        if capacity_items <= 0:
            raise ValueError("capacity_items must be positive")
        self.capacity_items = capacity_items
        self._records: OrderedDict[str, ContextFragment] = OrderedDict()

    def put(self, fragment: ContextFragment) -> None:
        if hashlib.sha256(fragment.content).hexdigest() != fragment.content_hash:
            raise ValueError("fragment content hash mismatch")
        if not fragment.requires_reverification:
            raise ValueError("prototype cache cannot store verifier-bypassing fragments")
        key = fragment.identity.canonical_key()
        self._records[key] = fragment
        self._records.move_to_end(key)
        while len(self._records) > self.capacity_items:
            self._records.popitem(last=False)

    def lookup(
        self,
        identity: ContextFragmentIdentity,
        *,
        requested_disclosure_class: str,
    ) -> CacheLookup:
        if requested_disclosure_class not in {"local_only", "remote"}:
            raise ValueError("unsupported requested disclosure class")
        key = identity.canonical_key()
        fragment = self._records.get(key)
        if fragment is None:
            return CacheLookup(CacheLookupStatus.MISS, None, "identity_miss")
        if hashlib.sha256(fragment.content).hexdigest() != fragment.content_hash:
            return CacheLookup(CacheLookupStatus.TAMPERED, None, "content_hash_mismatch")
        if fragment.identity != identity:
            return CacheLookup(CacheLookupStatus.TAMPERED, None, "key_identity_mismatch")
        if not fragment.requires_reverification:
            return CacheLookup(CacheLookupStatus.TAMPERED, None, "verifier_bypass_flag")
        if (
            fragment.identity.disclosure_class == "local_only"
            and requested_disclosure_class == "remote"
        ):
            return CacheLookup(CacheLookupStatus.POLICY_BLOCK, None, "privacy_non_promotion")
        return CacheLookup(CacheLookupStatus.HIT, fragment, "exact_identity")

    def keys(self) -> tuple[str, ...]:
        return tuple(self._records.keys())


# ---------------------------------------------------------------------------
# Q7 evidence-gated compute escalation model


class EscalationAction(str, Enum):
    ACCEPT = "ACCEPT"
    ESCALATE = "ESCALATE"
    BLOCKED_PRIVACY = "BLOCKED_PRIVACY"
    BLOCKED_BUDGET = "BLOCKED_BUDGET"
    TERMINAL_UNRESOLVED = "TERMINAL_UNRESOLVED"


@dataclass(frozen=True)
class TierSpec:
    name: str
    remote: bool
    cost_units: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("tier name is required")
        if self.cost_units < 0:
            raise ValueError("tier cost cannot be negative")


@dataclass(frozen=True)
class EscalationDecision:
    action: EscalationAction
    current_tier: str
    next_tier: Optional[str]
    preserved_outcome: str
    reason: str


class EscalationPolicy:
    def __init__(self, tiers: tuple[TierSpec, ...]):
        if not tiers:
            raise ValueError("at least one tier is required")
        self.tiers = tiers

    def decide(
        self,
        tier_index: int,
        verifier_outcome: str,
        *,
        remaining_budget: float,
        remote_allowed: bool,
    ) -> EscalationDecision:
        if not 0 <= tier_index < len(self.tiers):
            raise IndexError("tier_index out of range")
        if remaining_budget < 0:
            raise ValueError("remaining budget cannot be negative")
        current = self.tiers[tier_index]
        outcome = verifier_outcome.upper()
        if outcome == "PASS":
            return EscalationDecision(
                EscalationAction.ACCEPT,
                current.name,
                None,
                "PASS",
                "independent_verifier_pass",
            )
        if outcome not in {"FAIL", "UNKNOWN", "PROVIDER_ERROR", "ABSTAIN"}:
            return EscalationDecision(
                EscalationAction.TERMINAL_UNRESOLVED,
                current.name,
                None,
                outcome,
                "unrecognized_terminal",
            )
        next_index = tier_index + 1
        if next_index >= len(self.tiers):
            return EscalationDecision(
                EscalationAction.TERMINAL_UNRESOLVED,
                current.name,
                None,
                outcome,
                "no_next_tier",
            )
        nxt = self.tiers[next_index]
        if nxt.remote and not remote_allowed:
            return EscalationDecision(
                EscalationAction.BLOCKED_PRIVACY,
                current.name,
                None,
                outcome,
                "placement_ineligible",
            )
        if nxt.cost_units > remaining_budget:
            return EscalationDecision(
                EscalationAction.BLOCKED_BUDGET,
                current.name,
                None,
                outcome,
                "budget_reservation_failed",
            )
        return EscalationDecision(
            EscalationAction.ESCALATE,
            current.name,
            nxt.name,
            outcome,
            "policy_allows_unresolved_escalation",
        )


# ---------------------------------------------------------------------------
# Q8 hard-constraint-first empirical routing model


@dataclass(frozen=True)
class RoutingCandidate:
    candidate_id: str
    capabilities: FrozenSet[str]
    remote: bool
    estimated_cost: Optional[float]
    estimated_latency_ms: Optional[float]
    topology: str
    profile_revision: str

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.topology or not self.profile_revision:
            raise ValueError("candidate identity/topology/profile revision required")
        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError("estimated cost cannot be negative")
        if self.estimated_latency_ms is not None and self.estimated_latency_ms < 0:
            raise ValueError("estimated latency cannot be negative")


@dataclass(frozen=True)
class RoutingRequest:
    required_capabilities: FrozenSet[str]
    remote_allowed: bool
    remaining_budget: Optional[float]
    max_latency_ms: Optional[float]

    def __post_init__(self) -> None:
        if self.remaining_budget is not None and self.remaining_budget < 0:
            raise ValueError("remaining budget cannot be negative")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ValueError("latency ceiling cannot be negative")


@dataclass(frozen=True)
class RoutingProfile:
    profile_revision: str
    attempts: int
    verifier_passes: int
    mean_latency_ms: Optional[float]
    mean_cost: Optional[float]
    orchestration_tax: Optional[float]

    def __post_init__(self) -> None:
        if not self.profile_revision:
            raise ValueError("profile revision is required")
        if self.attempts < 0 or self.verifier_passes < 0:
            raise ValueError("profile counts cannot be negative")
        if self.verifier_passes > self.attempts:
            raise ValueError("verifier passes cannot exceed attempts")
        for value, name in (
            (self.mean_latency_ms, "mean_latency_ms"),
            (self.mean_cost, "mean_cost"),
            (self.orchestration_tax, "orchestration_tax"),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")

    @property
    def pass_posterior_mean(self) -> float:
        return (self.verifier_passes + 1) / (self.attempts + 2)

    @property
    def uncertainty(self) -> float:
        a = self.verifier_passes + 1
        b = max(0, self.attempts - self.verifier_passes) + 1
        denom = (a + b) ** 2 * (a + b + 1)
        return sqrt((a * b) / denom)


@dataclass(frozen=True)
class RoutingDecision:
    selected: Optional[str]
    feasible: tuple[str, ...]
    cold_start: tuple[str, ...]
    excluded: tuple[tuple[str, str], ...]
    reason: str
    scores: tuple[tuple[str, float], ...]


class RoutingModel:
    """Deterministic advisory router; hard constraints always dominate."""

    def __init__(
        self,
        uncertainty_weight: float = 0.5,
        unknown_metric_penalty: float = 0.25,
    ):
        if uncertainty_weight < 0 or unknown_metric_penalty < 0:
            raise ValueError("routing weights cannot be negative")
        self.uncertainty_weight = uncertainty_weight
        self.unknown_metric_penalty = unknown_metric_penalty

    def route(
        self,
        request: RoutingRequest,
        candidates: tuple[RoutingCandidate, ...],
        profiles: dict[str, RoutingProfile],
    ) -> RoutingDecision:
        feasible: list[RoutingCandidate] = []
        excluded: list[tuple[str, str]] = []
        for candidate in candidates:
            reason = None
            if not request.required_capabilities.issubset(candidate.capabilities):
                reason = "capability_ineligible"
            elif candidate.remote and not request.remote_allowed:
                reason = "placement_ineligible"
            elif request.remaining_budget is not None:
                if candidate.estimated_cost is None:
                    reason = "budget_unknown"
                elif candidate.estimated_cost > request.remaining_budget:
                    reason = "budget_ineligible"
            if reason is None and request.max_latency_ms is not None:
                if candidate.estimated_latency_ms is None:
                    reason = "latency_unknown"
                elif candidate.estimated_latency_ms > request.max_latency_ms:
                    reason = "deadline_ineligible"
            if reason is not None:
                excluded.append((candidate.candidate_id, reason))
            else:
                feasible.append(candidate)

        feasible.sort(key=lambda candidate: candidate.candidate_id)
        excluded.sort()
        if not feasible:
            return RoutingDecision(
                selected=None,
                feasible=(),
                cold_start=(),
                excluded=tuple(excluded),
                reason="no_hard_feasible_candidate",
                scores=(),
            )

        scored: list[tuple[str, float]] = []
        cold: list[str] = []
        for candidate in feasible:
            profile = profiles.get(candidate.candidate_id)
            if (
                profile is None
                or profile.attempts <= 0
                or profile.profile_revision != candidate.profile_revision
            ):
                cold.append(candidate.candidate_id)
                score = -1.0
            else:
                score = (
                    profile.pass_posterior_mean
                    - self.uncertainty_weight * profile.uncertainty
                )
                if profile.mean_latency_ms is None:
                    score -= self.unknown_metric_penalty
                else:
                    score -= min(profile.mean_latency_ms / 100_000.0, 1.0)
                if profile.mean_cost is None:
                    score -= self.unknown_metric_penalty
                else:
                    score -= min(profile.mean_cost / 1000.0, 1.0)
                if profile.orchestration_tax is None:
                    score -= self.unknown_metric_penalty
                else:
                    score -= min(profile.orchestration_tax / 100.0, 1.0)
            scored.append((candidate.candidate_id, score))

        scored.sort(key=lambda item: (-item[1], item[0]))
        return RoutingDecision(
            selected=scored[0][0],
            feasible=tuple(candidate.candidate_id for candidate in feasible),
            cold_start=tuple(sorted(cold)),
            excluded=tuple(excluded),
            reason="deterministic_empirical_score",
            scores=tuple(scored),
        )


def decision_digest(value) -> str:
    payload = json.dumps(
        asdict(value),
        sort_keys=True,
        separators=(",", ":"),
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def frozen_policy_evidence() -> dict:
    """Small retained Q5-Q8 model decisions for the evidence bundle."""

    pressure = PressurePolicy(PressurePolicyConfig()).decide(
        PressureInput(
            ready_frontier_depth=3,
            global_in_flight=1,
            mission_in_flight=1,
            pending_verifications=4,
            integration_queue_depth=0,
        )
    )
    identity = ContextFragmentIdentity(
        "ctx.v1",
        "o1",
        "contract",
        "a.txt",
        "sha",
        0,
        10,
        (),
        "verifier.v1",
        "remote",
        "template.v1",
    )
    cache = ContextCacheModel(2)
    cache.put(ContextFragment.create(identity, b"bounded context"))
    cache_lookup = cache.lookup(identity, requested_disclosure_class="remote")
    escalation = EscalationPolicy(
        (TierSpec("cheap", False, 1), TierSpec("expert", True, 5))
    ).decide(0, "UNKNOWN", remaining_budget=10, remote_allowed=True)
    routing = RoutingModel().route(
        RoutingRequest(frozenset({"text"}), True, 10, 5000),
        (
            RoutingCandidate("a", frozenset({"text"}), False, 1, 20, "single", "r1"),
            RoutingCandidate("b", frozenset({"text"}), True, 2, 15, "pair", "r1"),
        ),
        {
            "a": RoutingProfile("r1", 20, 15, 20, 1, 0.1),
            "b": RoutingProfile("r1", 2, 2, 15, 2, 0.2),
        },
    )
    return {
        "pressure": asdict(pressure),
        "cache": {
            "status": cache_lookup.status.value,
            "reason": cache_lookup.reason,
            "requires_reverification": cache_lookup.fragment.requires_reverification
            if cache_lookup.fragment
            else None,
        },
        "escalation": asdict(escalation),
        "routing": asdict(routing),
    }
