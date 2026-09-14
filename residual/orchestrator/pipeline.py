"""End-to-end orchestration pipeline facade.

ORCH-I-R19: The pipeline MUST compose compiler -> ambiguity -> partition
            -> risk -> plan in a fixed order; no stage MAY be skipped.
"""
from __future__ import annotations

from ..core import ContractError
from .ambiguity import AmbiguityDetector
from .compiler import RequirementCompiler
from .intent import Intent
from .partition import WorkPartitioner
from .plan import Plan
from .risk import RiskEstimator


class Orchestrator:
    """Fixed-order composition of the orchestration stages."""

    def __init__(self, compiler: RequirementCompiler | None = None,
                 detector: AmbiguityDetector | None = None,
                 partitioner: WorkPartitioner | None = None,
                 estimator: RiskEstimator | None = None):
        self._compiler = compiler or RequirementCompiler()
        self._detector = detector or AmbiguityDetector()
        self._partitioner = partitioner or WorkPartitioner()
        self._estimator = estimator or RiskEstimator()

    def plan(self, intent: Intent) -> Plan:
        if not isinstance(intent, Intent):
            raise ContractError("plan requires an Intent")
        graph = self._compiler.compile(intent)
        ambiguity = self._detector.analyze(graph)
        packets = self._partitioner.partition(graph)
        risks = self._estimator.estimate(graph, packets)
        return Plan(intent=intent, requirements=graph.requirements,
                    packets=packets, risk_reports=risks, ambiguity=ambiguity)
