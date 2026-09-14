"""Tests for SPEC-ENT-003 Multi-Tenant Architecture (ENT3-R1..ENT3-R6)."""
from __future__ import annotations

import pytest

from residual.core import ContractError
from residual.tenancy import (
    DelegationEngine, DelegationGrant, FairScheduler, FederationAgreement,
    Job, PlatformFloors, PlatformOperator, Principal, Tenant, TenantLifecycle,
    TenantPolicy, TenantStore, validate_policy,
)


def make_tenants(*ids: str) -> dict[str, Tenant]:
    return {tid: Tenant(id=tid) for tid in ids}


# ---------------- ENT3-R1: independent per-tenant state ----------------

def test_r1_each_tenant_has_independent_registries_and_logs():
    a, b = Tenant(id="tenantA"), Tenant(id="tenantB")
    a.register_goalspec("goal.one", {"goal": 1})
    a.register_module("mod.alpha", {"module": 1})
    a.state.append_receipt({"receipt_hash": "0" * 64})
    a.state.append_observation({"obs": 1})
    a.state.enqueue_hitl({"req": 1})
    a.state.quarantine_policies.add("p1")
    a.state.brake_config["threshold"] = 0.5

    assert "goal.one" not in b.state.goalspec_registry
    assert "mod.alpha" not in b.state.module_registry
    assert b.state.receipt_chain == []
    assert b.state.observation_log == []
    assert b.state.hitl_queue == []
    assert b.state.quarantine_policies == set()
    assert b.state.brake_config == {}
    # Distinct containers, not shared references.
    assert a.state.receipt_chain is not b.state.receipt_chain
    assert a.state.goalspec_registry is not b.state.goalspec_registry


def test_r1_receipt_chain_is_sequenced_per_tenant():
    a = Tenant(id="tenantA")
    a.state.append_receipt({"receipt_hash": "1" * 64})
    a.state.append_receipt({"receipt_hash": "2" * 64})
    assert [r["sequence"] for r in a.state.receipt_chain] == [0, 1]
    assert (a.state.receipt_chain[0]["chain_digest"]
            != a.state.receipt_chain[1]["chain_digest"])


def test_r1_contract_validation():
    with pytest.raises(ContractError):
        Tenant(id="bad id!")
    with pytest.raises(ContractError):
        Tenant(id="ok", quota=0)
    t = Tenant(id="tenantA")
    with pytest.raises(ContractError):
        t.register_goalspec("goal.one", None) or t.register_goalspec("goal.one", None)
    with pytest.raises(ContractError):
        t.state.append_receipt(["not-a-dict"])


# ---------------- ENT3-R2: data-layer isolation ----------------

def test_r2_tenant_reads_own_data():
    store = TenantStore()
    p = Principal(tenant_id="tenantA")
    store.put(p, "tenantA", "receipts", {"r": 1})
    assert store.get(p, "tenantA", "receipts") == {"r": 1}
    assert store.query(p, "tenantA") == {"receipts": {"r": 1}}


def test_r2_cross_tenant_access_denied():
    store = TenantStore()
    store.put(Principal(tenant_id="tenantA"), "tenantA", "receipts", {"r": 1})
    intruder = Principal(tenant_id="tenantB")
    with pytest.raises(ContractError):
        store.get(intruder, "tenantA", "receipts")
    with pytest.raises(ContractError):
        store.query(intruder, "tenantA")
    with pytest.raises(ContractError):
        store.put(intruder, "tenantA", "receipts", {"evil": True})


def test_r2_admin_cannot_read_other_tenants_data():
    store = TenantStore()
    store.put(Principal(tenant_id="tenantA", admin=True), "tenantA",
              "observations", {"o": 1})
    admin_b = Principal(tenant_id="tenantB", admin=True)
    with pytest.raises(ContractError):
        store.get(admin_b, "tenantA", "observations")
    with pytest.raises(ContractError):
        store.query(admin_b, "tenantA")
    with pytest.raises(ContractError):
        store.put(admin_b, "tenantA", "observations", {"x": 2})


def test_r2_federation_agreement_permits_scoped_read_only():
    store = TenantStore()
    store.put(Principal(tenant_id="tenantA"), "tenantA", "receipts", {"r": 1})
    store.put(Principal(tenant_id="tenantA"), "tenantA", "state", {"s": 1})
    store.add_federation(FederationAgreement(
        grantor="tenantA", grantee="tenantB", resources=("receipts",)))
    fed = Principal(tenant_id="tenantB", admin=True)
    assert store.get(fed, "tenantA", "receipts") == {"r": 1}
    with pytest.raises(ContractError):  # not a federated resource
        store.get(fed, "tenantA", "state")
    with pytest.raises(ContractError):  # writes never permitted
        store.put(fed, "tenantA", "receipts", {"r": 2})


# ---------------- ENT3-R3: fair scheduling ----------------

def test_r3_quotas_configurable_and_jobs_run():
    sched = FairScheduler(workers=2)
    sched.set_quota("tenantA", 4)
    sched.set_quota("tenantB", 1)
    assert sched.quotas["tenantA"] == 4
    with pytest.raises(ContractError):
        sched.set_quota("tenantA", 0)
    for i in range(4):
        sched.submit(Job(id=f"a{i}", tenant_id="tenantA"))
    sched.submit(Job(id="b0", tenant_id="tenantB"))
    done = sched.run_until_idle()
    assert len(done) == 5
    assert sched.pending("tenantA") == 0 and sched.pending("tenantB") == 0


def test_r3_starvation_free_under_flood():
    sched = FairScheduler(workers=1)
    sched.set_quota("big", 8)
    sched.set_quota("small", 1)
    for i in range(40):
        sched.submit(Job(id=f"big{i}", tenant_id="big"))
    for i in range(3):
        sched.submit(Job(id=f"small{i}", tenant_id="small"))
    done = sched.run_until_idle()
    first_small = next(i for i, j in enumerate(done) if j.tenant_id == "small")
    # With DRR, small gets at least 1 credit per round (round = 2 tenants,
    # big can spend at most 8/round), so small's first job runs well before
    # the flood drains.
    assert first_small <= 9
    assert len(done) == 43


def test_r3_fairness_proportional_share():
    sched = FairScheduler(workers=1)
    sched.set_quota("heavy", 3)
    sched.set_quota("light", 1)
    for i in range(12):
        sched.submit(Job(id=f"h{i}", tenant_id="heavy"))
    for i in range(12):
        sched.submit(Job(id=f"l{i}", tenant_id="light"))
    done = sched.run_until_idle()
    first_eight = done[:8]
    assert sum(j.tenant_id == "heavy" for j in first_eight) >= 4
    assert sum(j.tenant_id == "light" for j in first_eight) >= 2


# ---------------- ENT3-R4: cross-tenant delegation ----------------

def setup_delegation():
    tenants = make_tenants("tenantA", "tenantB")
    engine = DelegationEngine(tenants=tenants)
    grant = DelegationGrant(id="grant1", grantor="tenantA", grantee="tenantB",
                            task_types=("restart",), resources=("worker-1",),
                            expires_at=100)
    engine.add_grant(grant)
    return tenants, engine, grant


def approve(engine, tenants, approval_id):
    for req in tenants["tenantA"].state.hitl_queue:
        if req["approval_id"] == approval_id:
            req["approved"] = True


def test_r4_scoped_time_limited_execution_with_hitl_and_dual_receipts():
    tenants, engine, grant = setup_delegation()
    approval_id = engine.request_approval("grant1", "restart", "worker-1", now=10)
    approve(engine, tenants, approval_id)
    receipt = engine.execute("grant1", "restart", "worker-1", now=10,
                             approval_id=approval_id, result={"ok": True})
    # Receipt visible to both tenants.
    assert receipt.receipt_hash in {
        r["receipt_hash"] for r in tenants["tenantA"].state.receipt_chain}
    assert receipt.receipt_hash in {
        r["receipt_hash"] for r in tenants["tenantB"].state.receipt_chain}


def test_r4_requires_per_execution_hitl_approval():
    tenants, engine, grant = setup_delegation()
    approval_id = engine.request_approval("grant1", "restart", "worker-1", now=10)
    with pytest.raises(ContractError):  # pending, not approved
        engine.execute("grant1", "restart", "worker-1", now=10,
                       approval_id=approval_id, result={})
    with pytest.raises(ContractError):  # no approval requested at all
        engine.execute("grant1", "restart", "worker-1", now=10,
                       approval_id="f" * 16, result={})


def test_r4_scope_and_expiry_enforced():
    tenants, engine, grant = setup_delegation()
    with pytest.raises(ContractError):  # wrong task type
        engine.request_approval("grant1", "delete", "worker-1", now=10)
    with pytest.raises(ContractError):  # wrong resource
        engine.request_approval("grant1", "restart", "worker-2", now=10)
    with pytest.raises(ContractError):  # expired
        engine.request_approval("grant1", "restart", "worker-1", now=101)


# ---------------- ENT3-R5: tenant policies vs platform floors ----------------

def test_r5_tenant_may_tighten_beyond_floors():
    floors = PlatformFloors(brake_floor=1.0, verification_minimum=2,
                            default_quarantine=frozenset({"unverified-receipt"}))
    policy = TenantPolicy(tenant_id="tenantA", brake_threshold=0.5,
                          verification_level=3,
                          quarantine_policies=frozenset(
                              {"unverified-receipt", "extra-strict"}),
                          module_denylist=frozenset({"risky-module"}))
    assert validate_policy(policy, floors) is policy


def test_r5_loosening_floors_rejected():
    floors = PlatformFloors(brake_floor=1.0, verification_minimum=2,
                            default_quarantine=frozenset({"unverified-receipt"}))
    with pytest.raises(ContractError):  # brake threshold above floor
        validate_policy(TenantPolicy(tenant_id="t", brake_threshold=2.0,
                                     verification_level=3,
                                     quarantine_policies=frozenset(
                                         {"unverified-receipt"})), floors)
    with pytest.raises(ContractError):  # verification below minimum
        validate_policy(TenantPolicy(tenant_id="t", brake_threshold=0.5,
                                     verification_level=1,
                                     quarantine_policies=frozenset(
                                         {"unverified-receipt"})), floors)
    with pytest.raises(ContractError):  # dropped platform quarantine policy
        validate_policy(TenantPolicy(tenant_id="t", brake_threshold=0.5,
                                     verification_level=3,
                                     quarantine_policies=frozenset()), floors)


def test_r5_allowlist_denylist_conflict_rejected():
    with pytest.raises(ContractError):
        TenantPolicy(tenant_id="t", brake_threshold=0.5, verification_level=1,
                     module_allowlist=frozenset({"m"}),
                     module_denylist=frozenset({"m"}))


# ---------------- ENT3-R6: privileged lifecycle ----------------

def test_r6_create_delete_require_platform_privileges():
    life = TenantLifecycle()
    user = PlatformOperator(id="bob", platform_admin=False)
    admin = PlatformOperator(id="root", platform_admin=True)
    with pytest.raises(ContractError):
        life.create_tenant(user, "tenantA")
    tenant = life.create_tenant(admin, "tenantA")
    assert tenant.id == "tenantA"
    with pytest.raises(ContractError):
        life.create_tenant(admin, "tenantA")  # duplicate
    with pytest.raises(ContractError):
        life.delete_tenant(user, "tenantA")


def test_r6_deletion_archives_destroys_and_emits_final_receipt():
    life = TenantLifecycle()
    admin = PlatformOperator(id="root", platform_admin=True)
    tenant = life.create_tenant(admin, "tenantA")
    tenant.register_goalspec("goal.one", {"g": 1})
    tenant.state.append_receipt({"receipt_hash": "a" * 64})
    tenant.state.append_observation({"obs": 1})
    tenant.state.enqueue_hitl({"req": 1})

    record = life.delete_tenant(admin, "tenantA")
    assert "tenantA" not in life.tenants
    assert record.archived_receipts[0]["receipt_hash"] == "a" * 64
    assert record.archived_observations == ({"obs": 1},)
    deletion = record.deletion_receipt
    assert deletion["kind"] == "tenant-deletion"
    assert deletion["tenant_id"] == "tenantA"
    assert deletion["receipt_count"] == 1 and deletion["observation_count"] == 1
    assert len(deletion["receipt_hash"]) == 64
    # State destroyed.
    assert tenant.state.receipt_chain == []
    assert tenant.state.observation_log == []
    assert tenant.state.goalspec_registry == {}
    assert tenant.state.hitl_queue == []
    # Archive retained; recreation of the same id blocked.
    assert life.archives["tenantA"] is record
    with pytest.raises(ContractError):
        life.create_tenant(admin, "tenantA")
    with pytest.raises(ContractError):
        life.delete_tenant(admin, "tenantA")
