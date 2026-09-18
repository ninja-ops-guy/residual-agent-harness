from __future__ import annotations

import json
from pathlib import PurePosixPath

from hypothesis import given, settings, strategies as st

from residual.core import ContractError
from residual.factory.worker_contract import WorkerContract
from residual.station.contracts import parse_spec, path_ok
from residual.receipts import StationReceipt


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


JSON_VALUE = st.recursive(
    st.none() | st.booleans() | st.integers(min_value=-(2**31), max_value=2**31-1)
    | st.floats(allow_nan=False, allow_infinity=False, width=32)
    | st.text(max_size=80),
    lambda children: st.lists(children, max_size=8)
    | st.dictionaries(st.text(max_size=30), children, max_size=8),
    max_leaves=40,
)


@given(value=JSON_VALUE)
@settings(max_examples=500, deadline=None, derandomize=True, database=None)
def test_arbitrary_json_manifest_is_rejected_as_contract_error_or_strictly_validated(value):
    markdown = "# Fuzz\n\n```json\n" + json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n```"
    try:
        manifest = parse_spec(markdown)
    except ContractError:
        return
    # A parser exception other than ContractError is a qualification failure: the
    # HTTP layer should not need to understand Python implementation exceptions.
    assert manifest["schema_version"] == 1
    assert 1 <= len(manifest["tasks"]) <= 100
    ids = [task["id"] for task in manifest["tasks"]]
    assert len(ids) == len(set(ids))
    for task in manifest["tasks"]:
        assert task["files"]
        assert 1 <= len(task["checks"]) <= 20
        assert task["route"] in {"local", "cloud"}
        assert all(dep in ids for dep in task["depends_on"])


@given(value=JSON_VALUE)
@settings(max_examples=500, deadline=None, derandomize=True, database=None)
def test_arbitrary_json_receipt_never_normalizes_invalid_wire_data(value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
    try:
        receipt = StationReceipt.from_json(raw)
    except ContractError:
        return
    envelope = receipt.to_dict()
    assert envelope["receipt_hash"] == receipt.receipt_hash
    assert StationReceipt.from_dict(envelope) == receipt


def test_duplicate_keys_are_rejected_in_specs_and_receipts():
    bad_spec = '# Fuzz\n\n```json\n{"schema_version":1,"schema_version":1}\n```'
    with pytest.raises(ContractError):
        parse_spec(bad_spec)
    with pytest.raises(ContractError):
        StationReceipt.from_json('{"schema_version":"x","schema_version":"x"}')
