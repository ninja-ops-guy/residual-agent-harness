from __future__ import annotations

from pathlib import PurePosixPath

from hypothesis import given, settings, strategies as st

from residual.core import ContractError
from residual.factory.worker_contract import WorkerContract
from residual.station.contracts import path_ok


SEGMENT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-", min_size=1, max_size=20).filter(
    lambda value: value not in {".", "..", ".git", ".residual", ".env"} and not value.startswith("-")
)


def contract(parent: str, forbidden: str) -> WorkerContract:
    return WorkerContract(
        task_id="TaskA", worker_id="WorkerA", swarm_id="Fuzz",
        execution_plan_hash="a" * 64, attempt_id="AttemptA", lease_id="LeaseA",
        lease_generation=1, input_commit="b" * 40, workspace_root="/tmp/fuzz",
        inputs=(parent + "/",), allowed_outputs=(parent + "/",), forbidden=(forbidden + "/",),
        requirements=("ReqA",), acceptance=("CheckA",), dependencies=(),
        allowed_tools=("python",), forbidden_tools=("shell",), token_budget=100,
        wall_clock_budget_s=5, max_tool_calls=2, max_file_writes=2, memory_limit_mb=128,
    )


@given(parent=SEGMENT, child=SEGMENT, leaf=SEGMENT)
@settings(max_examples=250, deadline=None, derandomize=True, database=None)
def test_forbidden_descendant_always_overrides_broad_allowlist(parent: str, child: str, leaf: str):
    forbidden = f"{parent}/{child}"
    c = contract(parent, forbidden)
    target = f"{forbidden}/{leaf}.txt"
    assert not c.permits_path(target)
    assert not c.permits_path(target, write=True)


@given(prefix=SEGMENT, suffix=SEGMENT, variant=st.sampled_from([".git", ".GIT", ".Git", ".gIt"]))
@settings(max_examples=160, deadline=None, derandomize=True, database=None)
def test_git_metadata_segment_is_case_insensitively_forbidden(prefix: str, suffix: str, variant: str):
    c = WorkerContract(
        task_id="TaskA", worker_id="WorkerA", swarm_id="Fuzz",
        execution_plan_hash="a" * 64, attempt_id="AttemptA", lease_id="LeaseA",
        lease_generation=1, input_commit="b" * 40, workspace_root="/tmp/fuzz",
        inputs=(prefix + "/",), allowed_outputs=(prefix + "/",), forbidden=(),
        requirements=("ReqA",), acceptance=("CheckA",), dependencies=(),
        allowed_tools=("python",), forbidden_tools=("shell",), token_budget=100,
        wall_clock_budget_s=5, max_tool_calls=2, max_file_writes=2, memory_limit_mb=128,
    )
    target = f"{prefix}/{variant}/{suffix}"
    assert not c.permits_path(target)
    assert not c.permits_path(target, write=True)


@given(value=st.text(min_size=1, max_size=260))
@settings(max_examples=500, deadline=None, derandomize=True, database=None)
def test_station_path_acceptance_implies_workspace_safe_normalized_relative_path(value: str):
    try:
        accepted = path_ok(value)
    except (ContractError, ValueError):
        return
    path = PurePosixPath(accepted)
    assert not path.is_absolute()
    assert "\\" not in accepted
    assert "\x00" not in accepted
    assert ":" not in accepted
    assert not accepted.startswith("-")
    assert len(accepted) <= 240
    assert all(part not in {"..", ".git", ".residual", ".env"} for part in path.parts)
    assert all(not (part.startswith(".env.") and part not in {".env.example", ".env.template"}) for part in path.parts)
