from residual.orchestrator import (
    RiskEstimator,
    Requirement,
    RequirementGraph,
    WorkPartitioner,
    FAN_OUT_WEIGHT,
    PROTECTED_WEIGHT,
    EXTERNAL_IO_WEIGHT,
)


def req(rid, deps=(), files=(), external_io=False):
    return Requirement(requirement_id=rid, description=f"do {rid}",
                       depends_on=tuple(deps), files=tuple(files),
                       external_io=external_io)


def test_independent_requirements_get_separate_packets_same_level():
    graph = RequirementGraph([
        req("a", files=("residual/a.py",)),
        req("b", files=("residual/b.py",)),
        req("c", deps=("a", "b")),
    ])
    packets = WorkPartitioner().partition(graph)
    level0 = [p for p in packets if p.level == 0]
    assert len(level0) == 2
    assert {p.requirement_ids for p in level0} == {("a",), ("b",)}
    level1 = [p for p in packets if p.level == 1]
    assert len(level1) == 1 and level1[0].requirement_ids == ("c",)


def test_file_conflict_merges_into_serial_packet():
    graph = RequirementGraph([
        req("a", files=("shared/x.py",)),
        req("b", files=("shared/x.py", "shared/y.py")),
        req("c", files=("other.py",)),
    ])
    packets = WorkPartitioner().partition(graph)
    assert len(packets) == 2
    merged = next(p for p in packets if "b" in p.requirement_ids)
    assert merged.requirement_ids == ("a", "b")
    assert merged.files == ("shared/x.py", "shared/y.py")


def test_transitive_conflict_collapses():
    graph = RequirementGraph([
        req("a", files=("f1",)),
        req("b", files=("f1", "f2")),
        req("c", files=("f2",)),
    ])
    packets = WorkPartitioner().partition(graph)
    assert len(packets) == 1
    assert packets[0].requirement_ids == ("a", "b", "c")


def test_partition_deterministic():
    graph = RequirementGraph([req("a", files=("x",)), req("b", files=("y",)),
                              req("c", deps=("a",))])
    from residual.core import canonical
    results = {canonical([p.to_dict() for p in WorkPartitioner().partition(graph)])
               for _ in range(10)}
    assert len(results) == 1


def test_packet_ids_deterministic():
    graph = RequirementGraph([req("b"), req("a")])
    packets = WorkPartitioner().partition(graph)
    assert [p.packet_id for p in packets] == ["packet-0-0", "packet-0-1"]


def test_risk_scoring_formula():
    graph = RequirementGraph([
        req("root", files=("residual/evidence/bus.py",), external_io=True),
        req("child", deps=("root",)),
        req("child2", deps=("root",)),
    ])
    packets = WorkPartitioner().partition(graph)
    reports = {r.packet_id: r for r in RiskEstimator().estimate(graph, packets)}
    root_packet = next(p for p in packets if "root" in p.requirement_ids)
    report = reports[root_packet.packet_id]
    assert report.fan_out == 2
    assert report.protected_hits == 1
    assert report.external_io_count == 1
    assert report.score == (FAN_OUT_WEIGHT * 2 + PROTECTED_WEIGHT * 1
                            + EXTERNAL_IO_WEIGHT * 1)


def test_risk_custom_protected_prefixes():
    graph = RequirementGraph([req("a", files=("secret/keys.pem",))])
    packets = WorkPartitioner().partition(graph)
    default = RiskEstimator().estimate(graph, packets)[0]
    custom = RiskEstimator(protected_prefixes=("secret/",)).estimate(graph, packets)[0]
    assert default.protected_hits == 0
    assert custom.protected_hits == 1
    assert custom.score > default.score


def test_risk_zero_for_isolated_packet():
    graph = RequirementGraph([req("solo")])
    packets = WorkPartitioner().partition(graph)
    report = RiskEstimator().estimate(graph, packets)[0]
    assert report.score == 0
