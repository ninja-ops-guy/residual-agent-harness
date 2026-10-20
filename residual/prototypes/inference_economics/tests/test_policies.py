from dataclasses import replace

import pytest

from residual.prototypes.inference_economics.policies import (
    AdmissionAction,
    CacheLookupStatus,
    ContextCacheModel,
    ContextFragment,
    ContextFragmentIdentity,
    EscalationAction,
    EscalationPolicy,
    PressureInput,
    PressurePolicy,
    PressurePolicyConfig,
    RoutingCandidate,
    RoutingModel,
    RoutingProfile,
    RoutingRequest,
    TierSpec,
    decision_digest,
    frozen_policy_evidence,
)


def pressure_policy():
    return PressurePolicy(PressurePolicyConfig())


def pressure_input(**changes):
    values = dict(
        ready_frontier_depth=2,
        global_in_flight=1,
        mission_in_flight=1,
        pending_verifications=0,
        integration_queue_depth=0,
    )
    values.update(changes)
    return PressureInput(**values)


def identity(**changes):
    values = dict(
        schema_revision="ctx.v1",
        obligation_id="o1",
        contract_hash="contract",
        artifact_path="a.txt",
        artifact_content_hash="sha-a",
        window_start=0,
        window_end=10,
        dependency_receipt_hashes=("receipt-1",),
        verifier_revision="verifier.v1",
        disclosure_class="remote",
        template_revision="template.v1",
    )
    values.update(changes)
    return ContextFragmentIdentity(**values)


def route_candidate(name="a", **changes):
    values = dict(
        candidate_id=name,
        capabilities=frozenset({"text", "tool"}),
        remote=False,
        estimated_cost=1.0,
        estimated_latency_ms=20.0,
        topology="single",
        profile_revision="r1",
    )
    values.update(changes)
    return RoutingCandidate(**values)


def profile(**changes):
    values = dict(
        profile_revision="r1",
        attempts=20,
        verifier_passes=15,
        mean_latency_ms=20.0,
        mean_cost=1.0,
        orchestration_tax=0.1,
    )
    values.update(changes)
    return RoutingProfile(**values)


# Q5 pressure/backpressure

def test_pressure_admits_when_within_bounds():
    assert pressure_policy().decide(pressure_input()).action is AdmissionAction.ADMIT


def test_pressure_pauses_at_verifier_high_watermark():
    result = pressure_policy().decide(pressure_input(pending_verifications=4))
    assert result.action is AdmissionAction.PAUSE
    assert result.reason == "verifier_high_watermark"


def test_pressure_pauses_at_integration_high_watermark():
    result = pressure_policy().decide(pressure_input(integration_queue_depth=4))
    assert result.action is AdmissionAction.PAUSE
    assert result.reason == "integration_high_watermark"


def test_pressure_hysteresis_requires_drain_to_low_watermark():
    still_paused = pressure_policy().decide(
        pressure_input(previously_paused=True, pending_verifications=3)
    )
    resumed = pressure_policy().decide(
        pressure_input(previously_paused=True, pending_verifications=2)
    )
    assert still_paused.reason == "hysteresis_drain"
    assert resumed.action is AdmissionAction.ADMIT


def test_pressure_never_exceeds_inflight_limits():
    assert pressure_policy().decide(pressure_input(global_in_flight=4)).reason == "global_in_flight_limit"
    assert pressure_policy().decide(pressure_input(mission_in_flight=2)).reason == "mission_in_flight_limit"


def test_pressure_cancellation_while_waiting_never_dispatches():
    result = pressure_policy().decide(pressure_input(canceled=True, pending_verifications=8))
    assert result.action is AdmissionAction.CANCEL


def test_pressure_overload_is_typed_and_drops_nothing():
    result = pressure_policy().decide(pressure_input(pending_verifications=9))
    assert result.action is AdmissionAction.OVERLOAD
    assert result.dropped_work == 0


def test_pressure_decision_is_deterministic():
    state = pressure_input(pending_verifications=4)
    assert pressure_policy().decide(state) == pressure_policy().decide(state)


# Q6 provenance-safe cache

def test_exact_cache_identity_reuses_and_requires_reverification():
    cache = ContextCacheModel(2)
    item = ContextFragment.create(identity(), b"content")
    cache.put(item)
    lookup = cache.lookup(identity(), requested_disclosure_class="remote")
    assert lookup.status is CacheLookupStatus.HIT
    assert lookup.fragment.requires_reverification is True


@pytest.mark.parametrize("change", [
    {"artifact_content_hash": "changed"},
    {"contract_hash": "changed"},
    {"dependency_receipt_hashes": ("receipt-2",)},
    {"verifier_revision": "verifier.v2"},
    {"template_revision": "template.v2"},
    {"window_end": 11},
])
def test_normative_cache_identity_change_invalidates_reuse(change):
    cache = ContextCacheModel(2)
    original = identity()
    cache.put(ContextFragment.create(original, b"content"))
    lookup = cache.lookup(replace(original, **change), requested_disclosure_class="remote")
    assert lookup.status is CacheLookupStatus.MISS


def test_local_only_cache_fragment_cannot_be_promoted_remote():
    local = identity(disclosure_class="local_only")
    cache = ContextCacheModel(2)
    cache.put(ContextFragment.create(local, b"secret"))
    lookup = cache.lookup(local, requested_disclosure_class="remote")
    assert lookup.status is CacheLookupStatus.POLICY_BLOCK
    assert lookup.fragment is None


def test_cache_tamper_is_detected():
    item = ContextFragment.create(identity(), b"content")
    cache = ContextCacheModel(2)
    cache.put(item)
    cache._records[item.identity.canonical_key()] = ContextFragment(
        item.identity, b"changed", item.content_hash, True
    )
    assert cache.lookup(identity(), requested_disclosure_class="remote").status is CacheLookupStatus.TAMPERED


def test_cache_capacity_is_bounded_with_deterministic_fifo_eviction():
    cache = ContextCacheModel(2)
    identities = [identity(obligation_id=f"o{i}") for i in range(3)]
    for item_identity in identities:
        cache.put(ContextFragment.create(item_identity, item_identity.obligation_id.encode()))
    assert len(cache.keys()) == 2
    assert cache.lookup(identities[0], requested_disclosure_class="remote").status is CacheLookupStatus.MISS
    assert cache.lookup(identities[2], requested_disclosure_class="remote").status is CacheLookupStatus.HIT


def test_cache_refuses_fragment_that_claims_verifier_bypass():
    item = ContextFragment(identity(), b"content", "bad", requires_reverification=False)
    with pytest.raises(ValueError):
        ContextCacheModel(2).put(item)


# Q7 evidence-gated escalation

def ladder():
    return EscalationPolicy((TierSpec("cheap", False, 1), TierSpec("expert", True, 5)))


def test_verifier_pass_stops_escalation():
    result = ladder().decide(0, "PASS", remaining_budget=10, remote_allowed=True)
    assert result.action is EscalationAction.ACCEPT
    assert result.next_tier is None


@pytest.mark.parametrize("outcome", ["FAIL", "UNKNOWN", "PROVIDER_ERROR", "ABSTAIN"])
def test_unresolved_outcome_can_escalate_without_becoming_pass(outcome):
    result = ladder().decide(0, outcome, remaining_budget=10, remote_allowed=True)
    assert result.action is EscalationAction.ESCALATE
    assert result.preserved_outcome == outcome
    assert result.next_tier == "expert"


def test_remote_escalation_is_blocked_by_privacy():
    result = ladder().decide(0, "UNKNOWN", remaining_budget=10, remote_allowed=False)
    assert result.action is EscalationAction.BLOCKED_PRIVACY
    assert result.preserved_outcome == "UNKNOWN"


def test_escalation_is_blocked_before_dispatch_when_budget_insufficient():
    result = ladder().decide(0, "FAIL", remaining_budget=4, remote_allowed=True)
    assert result.action is EscalationAction.BLOCKED_BUDGET


def test_last_tier_unresolved_remains_unresolved():
    result = ladder().decide(1, "UNKNOWN", remaining_budget=99, remote_allowed=True)
    assert result.action is EscalationAction.TERMINAL_UNRESOLVED


# Q8 routing

def test_routing_hard_capability_constraint_dominates_profile_score():
    candidates = (
        route_candidate("eligible"),
        route_candidate("missing", capabilities=frozenset({"text"})),
    )
    profiles = {
        "eligible": profile(verifier_passes=10, attempts=20),
        "missing": profile(verifier_passes=20, attempts=20),
    }
    result = RoutingModel().route(
        RoutingRequest(frozenset({"tool"}), True, 10, 100), candidates, profiles
    )
    assert result.selected == "eligible"
    assert ("missing", "capability_ineligible") in result.excluded


def test_routing_privacy_constraint_dominates_profile_score():
    candidates = (
        route_candidate("local"),
        route_candidate("remote", remote=True),
    )
    profiles = {
        "local": profile(verifier_passes=10, attempts=20),
        "remote": profile(verifier_passes=20, attempts=20),
    }
    result = RoutingModel().route(
        RoutingRequest(frozenset({"text"}), False, 10, 100), candidates, profiles
    )
    assert result.selected == "local"
    assert ("remote", "placement_ineligible") in result.excluded


def test_routing_unknown_cost_is_not_treated_as_zero_under_budget_gate():
    candidate = route_candidate("unknown", estimated_cost=None)
    result = RoutingModel().route(
        RoutingRequest(frozenset({"text"}), True, 10, None), (candidate,), {"unknown": profile()}
    )
    assert result.selected is None
    assert result.excluded == (("unknown", "budget_unknown"),)


def test_routing_unknown_latency_is_not_treated_as_zero_under_deadline_gate():
    candidate = route_candidate("unknown", estimated_latency_ms=None)
    result = RoutingModel().route(
        RoutingRequest(frozenset({"text"}), True, None, 100), (candidate,), {"unknown": profile()}
    )
    assert result.selected is None
    assert result.excluded == (("unknown", "latency_unknown"),)


def test_profile_revision_change_creates_cold_start():
    candidate = route_candidate("a", profile_revision="r2")
    result = RoutingModel().route(
        RoutingRequest(frozenset({"text"}), True, 10, 100), (candidate,), {"a": profile(profile_revision="r1")}
    )
    assert result.cold_start == ("a",)


def test_low_sample_perfect_record_has_more_uncertainty_than_large_sample_record():
    low = RoutingProfile("r1", 2, 2, 10, 1, 0.1)
    high = RoutingProfile("r1", 100, 90, 10, 1, 0.1)
    assert low.uncertainty > high.uncertainty


def test_routing_penalizes_missing_empirical_metrics_instead_of_zero_imputation():
    candidate_a = route_candidate("a")
    candidate_b = route_candidate("b")
    profiles = {
        "a": profile(),
        "b": profile(mean_latency_ms=None, mean_cost=None, orchestration_tax=None),
    }
    result = RoutingModel().route(
        RoutingRequest(frozenset({"text"}), True, 10, 100),
        (candidate_a, candidate_b),
        profiles,
    )
    assert result.selected == "a"


def test_routing_replay_digest_is_deterministic():
    candidates = (route_candidate("a"), route_candidate("b", remote=True))
    request = RoutingRequest(frozenset({"text"}), True, 10, 100)
    profiles = {"a": profile(), "b": profile(attempts=5, verifier_passes=5)}
    one = RoutingModel().route(request, candidates, profiles)
    two = RoutingModel().route(request, candidates, profiles)
    assert one == two
    assert decision_digest(one) == decision_digest(two)


def test_no_hard_feasible_candidate_is_explicit():
    result = RoutingModel().route(
        RoutingRequest(frozenset({"gpu"}), False, 0, 1),
        (route_candidate("a"),),
        {"a": profile()},
    )
    assert result.selected is None
    assert result.reason == "no_hard_feasible_candidate"


def test_frozen_policy_evidence_is_deterministic_and_complete():
    first = frozen_policy_evidence()
    second = frozen_policy_evidence()
    assert first == second
    assert set(first) == {"pressure", "cache", "escalation", "routing"}
