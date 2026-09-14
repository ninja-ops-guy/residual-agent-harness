"""Tests for residual/licensing (SPEC-ENT-007 ENT7-R1/R5/R6, SPEC-ENT-008 ENT8-R2/R7)."""
from __future__ import annotations

import pytest

from residual.core import ContractError
from residual.licensing import (Channel, GraduationEvaluation, License,
                                MeteringModel, MetricResult, PilotPlan, Role,
                                Severity, SlaTracker, SupportTier, Tier,
                                TrainingRecord, UsageMeter)


# --- ENT8-R7: flexible licensing -------------------------------------------

def test_open_tier_is_free_and_lacks_commercial_features():
    lic = License(licensee="acme", tier=Tier.OPEN, metering=MeteringModel.FLAT)
    assert lic.price() == 0.0
    assert lic.allows("task_execution")
    assert not lic.allows("multi_tenancy")
    with pytest.raises(ContractError):
        lic.require("ha_dr")


def test_commercial_tier_includes_enterprise_features():
    lic = License(licensee="acme", tier=Tier.COMMERCIAL,
                  metering=MeteringModel.PER_NODE, node_limit=5)
    for feature in ("multi_tenancy", "ha_dr", "compliance_reporting",
                    "premium_support"):
        lic.require(feature)


def test_educational_and_nonprofit_discounts():
    edu = License(licensee="uni", tier=Tier.EDUCATIONAL,
                  metering=MeteringModel.FLAT)
    npo = License(licensee="charity", tier=Tier.NONPROFIT,
                  metering=MeteringModel.FLAT)
    com = License(licensee="acme", tier=Tier.COMMERCIAL,
                  metering=MeteringModel.FLAT)
    assert edu.price() == com.price() * 0.5
    assert npo.price() == round(com.price() * 0.6, 2)


def test_per_node_metering_enforces_node_limit():
    lic = License(licensee="acme", tier=Tier.COMMERCIAL,
                  metering=MeteringModel.PER_NODE, node_limit=2)
    meter = UsageMeter(license=lic)
    meter.register_node(2)
    with pytest.raises(ContractError):
        meter.register_node(1)
    meter.deregister_node(1)
    meter.register_node(1)
    assert meter.overage()["active_nodes"] == 2


def test_per_task_metering_enforces_task_limit():
    lic = License(licensee="acme", tier=Tier.COMMERCIAL,
                  metering=MeteringModel.PER_TASK, task_limit=100)
    meter = UsageMeter(license=lic)
    meter.record_task(90)
    with pytest.raises(ContractError):
        meter.record_task(11)
    meter.record_task(10)
    assert meter.tasks_executed == 100


def test_flat_rate_has_no_usage_caps():
    lic = License(licensee="acme", tier=Tier.COMMERCIAL,
                  metering=MeteringModel.FLAT)
    meter = UsageMeter(license=lic)
    meter.register_node(50)
    meter.record_task(10**6)
    assert meter.overage()["metering"] == "flat"


def test_unknown_feature_rejected():
    with pytest.raises(ContractError):
        License(licensee="acme", tier=Tier.COMMERCIAL,
                metering=MeteringModel.FLAT,
                features=frozenset({"task_execution", "teleportation"}))


# --- ENT8-R2: support tiers and SLA timers ---------------------------------

def test_tier_sla_values():
    assert SlaTracker(SupportTier.STANDARD).response_sla(Severity.P1) == 24 * 3600
    assert SlaTracker(SupportTier.PREMIUM).response_sla(Severity.P1) == 4 * 3600
    assert SlaTracker(SupportTier.ENTERPRISE).response_sla(Severity.P1) == 3600


def test_channel_restrictions():
    std = SlaTracker(SupportTier.STANDARD)
    with pytest.raises(ContractError):
        std.open_case("case-1", Severity.P2, 1000.0, channel=Channel.PHONE)
    ent = SlaTracker(SupportTier.ENTERPRISE)
    ent.open_case("case-1", Severity.P1, 1000.0, channel=Channel.ONSITE)


def test_p1_response_within_and_beyond_sla():
    ent = SlaTracker(SupportTier.ENTERPRISE)
    ent.open_case("fast", Severity.P1, 0.0)
    ent.record_first_response("fast", 3599.0)
    assert not ent.breached("fast")
    ent.open_case("slow", Severity.P1, 0.0)
    ent.record_first_response("slow", 3601.0)
    assert ent.breached("slow")
    report = ent.compliance_report()
    assert report["breaches"] == ["slow"]
    assert report["within_sla"] == 1


def test_overdue_timer_for_unanswered_case():
    prem = SlaTracker(SupportTier.PREMIUM)
    prem.open_case("pending", Severity.P1, 0.0)
    assert not prem.overdue("pending", 4 * 3600 - 1)
    assert prem.overdue("pending", 4 * 3600 + 1)
    prem.record_first_response("pending", 4 * 3600 + 2)
    assert not prem.overdue("pending", 10**9)
    assert prem.breached("pending")


# --- ENT7-R1: pilot program and graduation criteria ------------------------

def make_plan() -> PilotPlan:
    return PilotPlan(
        pilot_id="pilot-1",
        scope=("payments-team", "staging-cluster"),
        success_metrics=("receipt_verification_rate", "p1_incidents"),
        duration_days=60,
        rollback_plan="disable Residual engines, restore manual workflows",
        graduation_criteria=("security_signoff", "rollback_rehearsed"),
    )


def test_pilot_plan_validation():
    with pytest.raises(ContractError):
        PilotPlan(pilot_id="p", scope=(), success_metrics=("m",),
                  duration_days=60, rollback_plan="r", graduation_criteria=("g",))
    with pytest.raises(ContractError):
        PilotPlan(pilot_id="p", scope=("s",), success_metrics=("m",),
                  duration_days=10, rollback_plan="r", graduation_criteria=("g",))
    with pytest.raises(ContractError):
        PilotPlan(pilot_id="p", scope=("s",), success_metrics=("m",),
                  duration_days=120, rollback_plan="r", graduation_criteria=("g",))
    with pytest.raises(ContractError):
        PilotPlan(pilot_id="p", scope=("s",), success_metrics=("m",),
                  duration_days=60, rollback_plan="", graduation_criteria=("g",))


def test_graduation_requires_all_metrics_and_criteria():
    ev = GraduationEvaluation(plan=make_plan())
    ev.record_metric(MetricResult("receipt_verification_rate", 99.0, 99.7))
    ev.record_metric(MetricResult("p1_incidents", 1.0, 0.0, lower_is_better=True))
    assert ev.metrics_passed()
    assert not ev.graduated()  # criteria not yet attested
    ev.attest_criterion("security_signoff")
    assert not ev.graduated()
    ev.attest_criterion("rollback_rehearsed")
    assert ev.graduated()
    assert ev.report()["graduated"] is True


def test_failed_metric_blocks_graduation():
    ev = GraduationEvaluation(plan=make_plan())
    ev.record_metric(MetricResult("receipt_verification_rate", 99.0, 95.0))
    ev.record_metric(MetricResult("p1_incidents", 1.0, 0.0, lower_is_better=True))
    ev.attest_criterion("security_signoff")
    ev.attest_criterion("rollback_rehearsed")
    assert not ev.graduated()
    assert ev.report()["metrics"]["receipt_verification_rate"]["met"] is False


def test_unknown_metric_or_criterion_rejected():
    ev = GraduationEvaluation(plan=make_plan())
    with pytest.raises(ContractError):
        ev.record_metric(MetricResult("nope", 1.0, 1.0))
    with pytest.raises(ContractError):
        ev.attest_criterion("nope")


# --- ENT7-R5 / ENT7-R6: role training with hands-on sandbox exercises ------

def test_training_requires_all_hands_on_exercises():
    rec = TrainingRecord(user_id="user-1", role=Role.OPERATOR)
    rec.watch_video("intro")
    assert not rec.completed()  # video-only is insufficient (ENT7-R6)
    for ex in ("execute_task", "approve_hitl_challenge"):
        rec.record_exercise(ex, sandboxed=True)
    assert not rec.completed()
    rec.record_exercise("respond_to_brake", sandboxed=True)
    assert rec.completed()
    assert rec.progress()["exercises_remaining"] == []


def test_exercises_must_be_sandboxed():
    rec = TrainingRecord(user_id="user-2", role=Role.AUDITOR)
    with pytest.raises(ContractError):
        rec.record_exercise("verify_receipt_chain", sandboxed=False)


def test_exercise_must_match_role_curriculum():
    rec = TrainingRecord(user_id="user-3", role=Role.DEVELOPER)
    with pytest.raises(ContractError):
        rec.record_exercise("approve_hitl_challenge", sandboxed=True)


def test_role_curricula_cover_spec_roles():
    from residual.licensing import REQUIRED_EXERCISES
    assert set(REQUIRED_EXERCISES) == {Role.OPERATOR, Role.ADMINISTRATOR,
                                       Role.DEVELOPER, Role.AUDITOR}
    assert all(REQUIRED_EXERCISES[r] for r in Role)
