import pytest

from residual.core import ContractError, digest
from residual.orchestrator import (
    CapabilityGrant,
    ExecutionProfile,
    FlowCompiler,
    Intent,
    Orchestrator,
    Requirement,
    RequirementCompiler,
    StageCheckpoint,
    StageDoor,
    StageKind,
    validate_resume,
)


def _specified(req_id, *, depends_on=(), files=(), external_io=False):
    return Requirement(
        requirement_id=req_id,
        description=f"do {req_id}",
        depends_on=depends_on,
        owner="engineer",
        acceptance_criteria=("tests pass",),
        measurable_condition="pytest exits zero",
        files=files,
        external_io=external_io,
    )


def test_orchestrator_flow_preserves_plan_hash():
    orch = Orchestrator()
    intent = Intent("build a calculator")
    plan = orch.plan(intent)
    flow = orch.flow(intent)
    assert flow.plan_hash == plan.plan_hash
    assert flow.stages[0].stage_id == "prepare"
    assert flow.stages[-2].stage_id == "verify"
    assert flow.stages[-1].stage_id == "integrate"


def test_identical_plan_produces_identical_flow_hash():
    intent = Intent("same", constraints=("b", "a"))
    a = Orchestrator().flow(intent)
    b = Orchestrator().flow(Intent("same", constraints=("a", "b")))
    assert a.flow_hash == b.flow_hash


def test_default_ambiguous_plan_is_reviewed_and_human_gated():
    flow = Orchestrator().flow(Intent("ambiguous"))
    assert flow.profile is ExecutionProfile.REVIEWED
    assert flow.stage("human-gate").kind is StageKind.HUMAN_GATE
    assert flow.stage("review").kind is StageKind.REVIEW


def test_small_fully_specified_plan_uses_single_agent():
    compiler = RequirementCompiler(lambda _: (
        _specified("goal", files=("src/a.py",)),
    ))
    flow = Orchestrator(compiler=compiler).flow(Intent("small"))
    assert flow.profile is ExecutionProfile.SINGLE
    assert all(s.stage_id != "human-gate" for s in flow.stages)
    assert all(s.stage_id != "review" for s in flow.stages)
    execute = next(s for s in flow.stages if s.stage_id.startswith("execute-"))
    assert execute.kind is StageKind.AGENT


def test_four_independent_packets_route_to_swarm():
    compiler = RequirementCompiler(lambda _: tuple(
        _specified(f"r{i}", files=(f"src/{i}.py",)) for i in range(4)
    ))
    flow = Orchestrator(compiler=compiler).flow(Intent("parallel"))
    assert flow.profile is ExecutionProfile.SWARM
    assert sum(s.kind is StageKind.SWARM for s in flow.stages) == 4
    assert flow.stage("review").kind is StageKind.REVIEW


def test_stage_dependencies_only_point_backward():
    flow = Orchestrator().flow(Intent("ordered"))
    seen = set()
    for stage in flow.stages:
        assert set(stage.depends_on) <= seen
        seen.add(stage.stage_id)


def test_deterministic_stages_have_zero_token_budget():
    flow = Orchestrator().flow(Intent("deterministic boundaries"))
    for stage in flow.stages:
        if stage.kind is StageKind.DETERMINISTIC:
            assert stage.budget.max_tokens == 0


def test_capability_door_denies_undeclared_operations():
    grant = CapabilityGrant(tools=("verifier.run",), paths=("src/",))
    stage = FlowCompiler().compile(Orchestrator().plan(Intent("gate"))).stage("verify")
    with pytest.raises(ContractError, match="tool outside"):
        StageDoor.authorize(stage, tool="shell.exec")
    with pytest.raises(ContractError, match="workspace write"):
        StageDoor.authorize(stage, write=True)

    grant.authorize(tool="verifier.run", path="src/a.py")
    with pytest.raises(ContractError, match="path outside"):
        grant.authorize(path="secrets/key.txt")


def test_checkpoint_resume_requires_exact_bindings():
    flow = Orchestrator().flow(Intent("resume"))
    cp = StageCheckpoint(
        flow_hash=flow.flow_hash,
        stage_id="prepare",
        input_hash=digest({"input": 1}),
        output_hash=digest({"output": 1}),
        repo_head_before="abc",
        repo_head_after="def",
        evidence_ids=("evidence-1",),
    )
    assert validate_resume(
        flow, cp, expected_input_hash=digest({"input": 1}), current_repo_head="def"
    ).reusable
    assert not validate_resume(
        flow, cp, expected_input_hash=digest({"input": 2}), current_repo_head="def"
    ).reusable
    assert not validate_resume(
        flow, cp, expected_input_hash=digest({"input": 1}), current_repo_head="moved"
    ).reusable


def test_integration_stage_is_deterministic_and_not_agent_capable():
    flow = Orchestrator().flow(Intent("integration boundary"))
    stage = flow.stage("integrate")
    assert stage.kind is StageKind.DETERMINISTIC
    assert stage.capability.workspace_write is True
    assert stage.capability.tools == ("integrator.apply",)
    with pytest.raises(ContractError):
        StageDoor.authorize(stage, tool="agent.execute")
