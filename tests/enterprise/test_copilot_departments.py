"""Department/RBAC qualification for Copilot Studio enterprise profiles."""
from __future__ import annotations

from residual.integrations.copilot_studio.auth import CopilotPrincipal
from residual.integrations.copilot_studio.departments import (
    DepartmentGroups, department_catalog,
)


def _principal(oid,groups):
    return CopilotPrincipal("tenant","sub-"+oid,oid,"issuer",frozenset({"access_as_user"}),frozenset(groups),frozenset())


def _groups(prefix):
    return DepartmentGroups(
        members=frozenset({prefix+"-members"}),
        reviewers=frozenset({prefix+"-reviewers"}),
        leads=frozenset({prefix+"-leads"}),
        auditors=frozenset({"engineering-auditors"}),
    )


def _catalog():
    return department_catalog({
        "firmware":_groups("fw"),
        "mechanical":_groups("mech"),
        "electromechanical":_groups("emech"),
        "automated_testing":_groups("test"),
        "quality_assurance":_groups("qa"),
    })


def test_all_five_departments_have_distinct_profiles_and_templates():
    catalog=_catalog()
    assert set(catalog)=={"firmware","mechanical","electromechanical","automated_testing","quality_assurance"}
    assert len({p.profile_id for p,_ in catalog.values()})==5
    assert all(templates for _,templates in catalog.values())


def test_member_can_submit_only_its_department_templates():
    catalog=_catalog()
    for name,(profile,templates) in catalog.items():
        member=_principal(name,{next(iter(profile.allowed_groups))})
        for template in templates.values():
            profile.authorize(member,template)
        for other,(other_profile,other_templates) in catalog.items():
            if other==name: continue
            # Different department group does not satisfy this profile membership.
            outsider=_principal("outsider",{next(iter(other_profile.allowed_groups))})
            try:
                profile.authorize(outsider,next(iter(templates.values())))
            except Exception:
                pass
            else:
                raise AssertionError("cross-department template access was allowed")


def test_reviewer_can_read_but_cannot_control_another_users_mission():
    profile,_=_catalog()["firmware"]
    owner="engineer-1"
    reviewer=_principal("reviewer-1",profile.reviewer_groups)
    assert profile.can_read_mission(reviewer,owner)
    assert not profile.can_control_mission(reviewer,owner)


def test_auditor_is_read_only_across_owned_mission():
    profile,_=_catalog()["quality_assurance"]
    auditor=_principal("auditor-1",profile.auditor_groups)
    assert profile.can_read_mission(auditor,"qa-engineer")
    assert not profile.can_control_mission(auditor,"qa-engineer")


def test_lead_can_read_and_control_department_mission():
    profile,_=_catalog()["mechanical"]
    lead=_principal("lead-1",profile.lead_groups)
    assert profile.can_read_mission(lead,"engineer-1")
    assert profile.can_control_mission(lead,"engineer-1")


def test_removed_owner_loses_read_and_control_access():
    profile,_=_catalog()["firmware"]
    former=_principal("owner",set())
    assert not profile.can_read_mission(former,"owner")
    assert not profile.can_control_mission(former,"owner")


def test_global_high_risk_capabilities_are_denied_everywhere():
    catalog=_catalog()
    forbidden={"pr.merge","production.write","policy.modify","qualification.bypass","verifier.bypass","secrets.read","shell.host","network.arbitrary"}
    for profile,_ in catalog.values():
        assert forbidden <= profile.deny_capabilities
        assert not (forbidden & profile.allow_capabilities)
