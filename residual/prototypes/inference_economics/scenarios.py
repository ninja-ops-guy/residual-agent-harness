"""Frozen deterministic scenarios for IE-001 qualification."""

from dataclasses import dataclass, field
from typing import Optional

from .metrics import BottleneckClass
from .stages import ResourceSignals, Stage


@dataclass(frozen=True)
class ScenarioStep:
    stage: Stage
    start_ns: Optional[int]
    end_ns: Optional[int]
    outcome: str = "PASS"
    obligation_id: str = "oblig-001"
    attempt_id: str = "attempt-001"
    resources: ResourceSignals = field(default_factory=ResourceSignals)


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    expected_bottleneck: BottleneckClass
    steps: tuple[ScenarioStep, ...]


def _linear(worker=(500, 1500), *, planning=(100, 200), scheduling=(200, 300), queue=(300, 400), context=(400, 500), evidence=None, verify=None, iq=None, integrate=None, worker_resources=None):
    w0, w1 = worker
    evidence = evidence or (w1, w1 + 100)
    verify = verify or (evidence[1], evidence[1] + 100)
    iq = iq or (verify[1], verify[1] + 50)
    integrate = integrate or (iq[1], iq[1] + 50)
    return (
        ScenarioStep(Stage.MISSION_SUBMIT, 0, 0),
        ScenarioStep(Stage.PLANNING, *planning),
        ScenarioStep(Stage.SCHEDULING, *scheduling),
        ScenarioStep(Stage.QUEUE_WAIT, *queue),
        ScenarioStep(Stage.CONTEXT_PACKAGING, *context),
        ScenarioStep(Stage.WORKER_EXECUTION, w0, w1, resources=worker_resources or ResourceSignals()),
        ScenarioStep(Stage.EVIDENCE_PUBLICATION, *evidence),
        ScenarioStep(Stage.VERIFICATION, *verify),
        ScenarioStep(Stage.INTEGRATION_QUEUE, *iq),
        ScenarioStep(Stage.INTEGRATION, *integrate),
        ScenarioStep(Stage.TERMINAL, integrate[1], integrate[1]),
    )


SCENARIO_WORKER_BOUND = Scenario(
    "worker_bound", "Worker service dominates.", BottleneckClass.WORKER_BOUND,
    _linear(worker=(500, 10_500)),
)

# Three parallel obligations with long verification service.
SCENARIO_VERIFIER_BOUND = Scenario(
    "verifier_bound", "Workers finish fast; verification dominates.", BottleneckClass.VERIFIER_BOUND,
    (
        ScenarioStep(Stage.MISSION_SUBMIT, 0, 0),
        ScenarioStep(Stage.PLANNING, 100, 200),
        ScenarioStep(Stage.SCHEDULING, 200, 300),
        ScenarioStep(Stage.QUEUE_WAIT, 300, 400),
        ScenarioStep(Stage.CONTEXT_PACKAGING, 400, 500),
        ScenarioStep(Stage.WORKER_EXECUTION, 500, 1_500, obligation_id="oblig-001"),
        ScenarioStep(Stage.WORKER_EXECUTION, 500, 1_500, obligation_id="oblig-002"),
        ScenarioStep(Stage.WORKER_EXECUTION, 500, 1_500, obligation_id="oblig-003"),
        ScenarioStep(Stage.EVIDENCE_PUBLICATION, 1_500, 1_600, obligation_id="oblig-001"),
        ScenarioStep(Stage.EVIDENCE_PUBLICATION, 1_500, 1_600, obligation_id="oblig-002"),
        ScenarioStep(Stage.EVIDENCE_PUBLICATION, 1_500, 1_600, obligation_id="oblig-003"),
        ScenarioStep(Stage.VERIFICATION, 1_600, 101_600, obligation_id="oblig-001"),
        ScenarioStep(Stage.VERIFICATION, 1_600, 101_600, obligation_id="oblig-002"),
        ScenarioStep(Stage.VERIFICATION, 1_600, 101_600, obligation_id="oblig-003"),
        ScenarioStep(Stage.INTEGRATION_QUEUE, 101_600, 101_650, obligation_id="oblig-001"),
        ScenarioStep(Stage.INTEGRATION, 101_650, 101_700, obligation_id="oblig-001"),
        ScenarioStep(Stage.TERMINAL, 101_700, 101_700, obligation_id="oblig-001"),
    ),
)

SCENARIO_CONTEXT_BOUND = Scenario(
    "context_bound", "Context packaging dominates.", BottleneckClass.CONTEXT_BOUND,
    _linear(worker=(50_400, 50_500), context=(400, 50_400)),
)

SCENARIO_INTEGRATION_BOUND = Scenario(
    "integration_bound", "Integration dominates.", BottleneckClass.INTEGRATION_BOUND,
    _linear(integrate=(1_750, 81_750)),
)

SCENARIO_COORDINATION_BOUND = Scenario(
    "coordination_bound", "Planning/coordination dominates.", BottleneckClass.COORDINATION_BOUND,
    _linear(worker=(60_400, 60_500), planning=(100, 60_100), scheduling=(60_100, 60_200), queue=(60_200, 60_300), context=(60_300, 60_400)),
)

SCENARIO_PROVIDER_BOUND = Scenario(
    "provider_bound", "Authoritative provider throttling plus worker wait dominates.", BottleneckClass.PROVIDER_BOUND,
    _linear(worker=(500, 200_500), worker_resources=ResourceSignals(provider_throttled=True)),
)

SCENARIO_SCHEDULER_ADMISSION_BOUND = Scenario(
    "scheduler_admission_bound", "Admission/queue wait dominates.", BottleneckClass.SCHEDULER_ADMISSION_BOUND,
    _linear(worker=(80_400, 80_500), queue=(300, 80_300), context=(80_300, 80_400)),
)

SCENARIO_MIXED = Scenario(
    "mixed", "No single stage dominates.", BottleneckClass.MIXED,
    (
        ScenarioStep(Stage.MISSION_SUBMIT, 0, 0),
        ScenarioStep(Stage.PLANNING, 100, 5_100),
        ScenarioStep(Stage.SCHEDULING, 5_100, 10_100),
        ScenarioStep(Stage.QUEUE_WAIT, 10_100, 15_100),
        ScenarioStep(Stage.CONTEXT_PACKAGING, 15_100, 20_100),
        ScenarioStep(Stage.WORKER_EXECUTION, 20_100, 25_100),
        ScenarioStep(Stage.EVIDENCE_PUBLICATION, 25_100, 30_100),
        ScenarioStep(Stage.VERIFICATION, 30_100, 35_100),
        ScenarioStep(Stage.INTEGRATION_QUEUE, 35_100, 40_100),
        ScenarioStep(Stage.INTEGRATION, 40_100, 45_100),
        ScenarioStep(Stage.TERMINAL, 45_100, 45_100),
    ),
)

SCENARIO_UNKNOWN_EVIDENCE = Scenario(
    "unknown_evidence", "Required observations are missing.", BottleneckClass.UNKNOWN,
    tuple(ScenarioStep(stage, None, None, outcome="UNKNOWN") for stage in (
        Stage.MISSION_SUBMIT, Stage.PLANNING, Stage.SCHEDULING, Stage.QUEUE_WAIT,
        Stage.CONTEXT_PACKAGING, Stage.WORKER_EXECUTION, Stage.EVIDENCE_PUBLICATION,
        Stage.VERIFICATION, Stage.TERMINAL,
    )),
)

ALL_SCENARIOS = (
    SCENARIO_WORKER_BOUND,
    SCENARIO_VERIFIER_BOUND,
    SCENARIO_CONTEXT_BOUND,
    SCENARIO_INTEGRATION_BOUND,
    SCENARIO_COORDINATION_BOUND,
    SCENARIO_PROVIDER_BOUND,
    SCENARIO_SCHEDULER_ADMISSION_BOUND,
    SCENARIO_MIXED,
    SCENARIO_UNKNOWN_EVIDENCE,
)
