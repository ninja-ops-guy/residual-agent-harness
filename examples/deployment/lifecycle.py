"""Runnable, deterministic lifecycle example; no model or network calls."""
from pathlib import Path
from tempfile import TemporaryDirectory

from residual import AmendmentRule, CheckResult, CheckType, GoalSpec, LoopController, SuccessCriterion, Verifier
from residual.core import digest
from residual.engines import CapabilityRouter, ContextAssembly, EngineHarnessPass, EngineHealth, EngineResult, TaskSpec
from residual.lifecycle import ModuleLifecycleBus, bind_memory, bind_trajectory, bind_tui
from residual.memory import EpistemicMemoryStore, MemoryContextAssembler, MemoryRequest
from residual.receipts import StationReceipt
from residual.trajectory import TrajectoryRecorder, GoldenTrajectoryStore
from residual.tui import ObservationCollector


class DeterministicEngine:
    name, version, capability_class, locality = 'example', '1', 'fixture', 'local'
    def supports(self, capability): return capability == 'arithmetic'
    def health(self): return EngineHealth.HEALTHY
    def normalize(self, raw): return EngineResult(raw, token_usage=0)
    def execute(self, task, context): return self.normalize(sum(task.input))


def run(directory):
    goal = GoalSpec('example', 'Compute 2+3',
        (SuccessCriterion('sum', CheckType.MECHANICAL, 'Must equal five', 'host'),),
        1, 100, 10, AmendmentRule(('operator',)))
    engine = DeterministicEngine(); router = CapabilityRouter(); router.register(engine,('arithmetic',))
    harness = EngineHarnessPass(router, lambda s,n:TaskSpec(s.goal_id,'arithmetic',[2,3]),
                                 lambda s,n:ContextAssembly())
    verifier = Verifier({'host':lambda value,parameters:(CheckResult.PASS if value == 5 else CheckResult.FAIL,'checked')})
    bus = ModuleLifecycleBus(include_metrics=False)
    recorder = TrajectoryRecorder(str(Path(directory)/'trajectories'))
    memory = EpistemicMemoryStore(str(Path(directory)/'memory'))
    # The host issues this fixture receipt only after its run verifies successfully.
    receipt = StationReceipt('sum', digest({'goal':goal.content_hash,'input':[2,3]}), digest(5),
        'host:sum', digest({'implementation':'fixture-equality-v1'}), CheckResult.PASS,
        engine_name=engine.name, engine_version=engine.version)
    trajectories = []; collector = ObservationCollector()
    bindings = [bind_trajectory(bus,recorder,publish=trajectories.append),
        bind_memory(bus,memory,lambda result:[('2+3',receipt,5)]), bind_tui(bus,collector)]
    try:
        result = LoopController(goal,verifier,harness,lifecycle=bus).run()
        request = MemoryRequest('sum','2+3',receipt.verifier_revision,
            lambda stored,value:stored.cache_key == receipt.cache_key and value == 5)
        context = MemoryContextAssembler(memory,(request,)).assemble()
        golden = GoldenTrajectoryStore(Path(directory)/'golden.sqlite3',recorder)
        golden.promote('example',trajectories[0].trajectory_hash)
        assert golden.compare('example',trajectories[0])[0]
        assert result.outcome.value == collector.snapshot().status == 'success'
        assert context.values['memory']['sum']['value'] == 5
        return {'outcome':result.outcome.value,'memory_value':5,'trajectory':trajectories[0].trajectory_hash}
    finally:
        for binding in bindings: binding.close()


if __name__ == '__main__':
    with TemporaryDirectory() as directory:
        print(run(directory))
