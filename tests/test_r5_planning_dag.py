from __future__ import annotations

import json
from pathlib import Path


DAG_PATH = Path(__file__).parents[1] / "docs" / "r5" / "R5_DAG.json"
REQUIRED_FIELDS = {
    "requirement_id", "category", "phase", "title", "dependencies",
    "invariant", "threat_failure_model", "positive_fixture",
    "negative_fixture", "adversarial_fixture", "deterministic_oracle",
    "qualification_gate", "evidence_required", "implementation_boundary",
    "rollback_implications", "research_relevance", "exit_criteria",
}


def load() -> dict:
    return json.loads(DAG_PATH.read_text(encoding="utf-8"))


def test_every_requirement_has_complete_contract_and_unique_gate() -> None:
    dag = load()
    requirements = dag["requirements"]
    assert len(requirements) == 17
    assert {item["category"] for item in requirements} == set("ABCDEFG")
    assert all(set(item) == REQUIRED_FIELDS for item in requirements)
    assert len({item["requirement_id"] for item in requirements}) == len(requirements)
    assert len({item["qualification_gate"] for item in requirements}) == len(requirements)
    for item in requirements:
        assert item["threat_failure_model"]
        assert item["evidence_required"]
        for field in REQUIRED_FIELDS - {"dependencies", "threat_failure_model", "evidence_required"}:
            assert item[field]


def test_dependency_graph_is_closed_and_acyclic() -> None:
    items = {item["requirement_id"]: item for item in load()["requirements"]}
    assert all(dep in items for item in items.values() for dep in item["dependencies"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        assert node not in visiting, f"dependency cycle at {node}"
        if node in visited:
            return
        visiting.add(node)
        for dependency in items[node]["dependencies"]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for requirement_id in items:
        visit(requirement_id)
    assert visited == set(items)


def test_phases_are_complete_disjoint_and_dependency_ordered() -> None:
    dag = load()
    items = {item["requirement_id"]: item for item in dag["requirements"]}
    phases = dag["phases"]
    phase_index = {phase["phase_id"]: index for index, phase in enumerate(phases)}
    flattened = [item for phase in phases for item in phase["requirements"]]
    assert len(phases) == 6
    assert len(flattened) == len(set(flattened))
    assert set(flattened) == set(items)
    assert len({phase["phase_gate"] for phase in phases}) == len(phases)
    for item in items.values():
        assert item["phase"] in phase_index
        for dependency in item["dependencies"]:
            assert phase_index[items[dependency]["phase"]] <= phase_index[item["phase"]]


def test_declared_critical_path_is_a_real_dependency_path() -> None:
    dag = load()
    items = {item["requirement_id"]: item for item in dag["requirements"]}
    path = dag["critical_path"]
    assert path[0] == "R5-SC-015"
    assert path[-1] == "R5-SC-017"
    for predecessor, successor in zip(path, path[1:]):
        assert predecessor in items[successor]["dependencies"]
