import pytest

from residual.core import ContractError
from residual.orchestrator import (
    AmbiguityDetector,
    Intent,
    MISSING_ACCEPTANCE,
    MISSING_MEASURABLE,
    MISSING_OWNER,
    Requirement,
    RequirementCompiler,
    RequirementGraph,
)


def req(rid, deps=(), **kw):
    return Requirement(requirement_id=rid, description=f"do {rid}", depends_on=tuple(deps), **kw)


def test_requirement_validation():
    with pytest.raises(ContractError):
        Requirement(requirement_id="bad id!", description="x")
    with pytest.raises(ContractError):
        Requirement(requirement_id="ok", description="  ")
    with pytest.raises(ContractError):
        Requirement(requirement_id="self", description="x", depends_on=("self",))
    with pytest.raises(ContractError):
        req("dup", deps=("a", "a"))


def test_graph_rejects_duplicates_and_dangling():
    with pytest.raises(ContractError):
        RequirementGraph([req("a"), req("a")])
    with pytest.raises(ContractError):
        RequirementGraph([req("a", deps=("missing",))])


def test_topological_order_respects_dependencies():
    graph = RequirementGraph([req("c", deps=("a", "b")), req("b"), req("a", deps=("b",))])
    order = graph.topological_order()
    assert order.index("b") < order.index("a") < order.index("c")


def test_topological_order_is_deterministic():
    reqs = [req("z"), req("m", deps=("z",)), req("a"), req("q", deps=("a",))]
    orders = {RequirementGraph(reqs).topological_order() for _ in range(10)}
    assert len(orders) == 1


def test_cycle_detection_raises_with_path():
    with pytest.raises(ContractError, match="cycle"):
        RequirementGraph([req("a", deps=("b",)), req("b", deps=("a",))])


def test_find_cycle_returns_path():
    with pytest.raises(ContractError) as excinfo:
        RequirementGraph([req("a", deps=("b",)), req("b", deps=("c",)), req("c", deps=("a",))])
    message = str(excinfo.value)
    assert "->" in message


def test_levels_group_independent_nodes():
    graph = RequirementGraph([req("c", deps=("a", "b")), req("a"), req("b")])
    levels = graph.levels()
    assert levels == (("a", "b"), ("c",))


def test_dependents():
    graph = RequirementGraph([req("c", deps=("a", "b")), req("a"), req("b")])
    assert graph.dependents("a") == ("c",)
    assert graph.dependents("c") == ()
    with pytest.raises(ContractError):
        graph.dependents("nope")


def test_default_compiler_shape():
    intent = Intent(goal="build x", constraints=("no net", "fast"),
                    context_refs=("docs/a.md",))
    graph = RequirementCompiler().compile(intent)
    ids = [r.requirement_id for r in graph.requirements]
    assert "goal" in ids
    assert any(i.startswith("context-") for i in ids)
    assert sum(i.startswith("constraint-") for i in ids) == 2
    goal = graph.get("goal")
    assert goal.depends_on == tuple(i for i in ids if i.startswith("context-"))
    for c in graph.requirements:
        if c.requirement_id.startswith("constraint-"):
            assert c.depends_on == ("goal",)


def test_compile_deterministic():
    intent = Intent(goal="build x", constraints=("c1", "c2"), context_refs=("r1",))
    g1 = RequirementCompiler().compile(intent)
    g2 = RequirementCompiler().compile(Intent(goal="build x",
                                              constraints=("c2", "c1"),
                                              context_refs=("r1",)))
    assert [r.to_dict() for r in g1.requirements] == [r.to_dict() for r in g2.requirements]
    assert g1.topological_order() == g2.topological_order()


def test_compile_rejects_empty_decomposition():
    with pytest.raises(ContractError):
        RequirementCompiler(decompose=lambda intent: []).compile(Intent(goal="g"))


def test_compile_rejects_non_intent():
    with pytest.raises(ContractError):
        RequirementCompiler().compile("not an intent")


def test_ambiguity_detector_flags_all_three_kinds():
    graph = RequirementGraph([req("bare")])
    report = AmbiguityDetector().analyze(graph)
    kinds = {f.kind for f in report.flags}
    assert kinds == {MISSING_OWNER, MISSING_ACCEPTANCE, MISSING_MEASURABLE}
    assert report.has_ambiguity


def test_ambiguity_detector_clean_requirement():
    good = Requirement(
        requirement_id="good",
        description="fully specified",
        owner="swarm-4",
        acceptance_criteria=("pytest green",),
        measurable_condition="591 tests pass",
    )
    report = AmbiguityDetector().analyze(RequirementGraph([good]))
    assert not report.has_ambiguity
    assert report.flags == ()
