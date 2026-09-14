"""Bridge a host-selected engine and context factory into the bounded controller."""
from __future__ import annotations
from ..core import ContractError
from .protocol import ContextAssembly, EngineResult, TaskSpec


class EngineHarnessPass:
    def __init__(self, router, task_factory, context_factory):
        self.router, self.task_factory, self.context_factory = router, task_factory, context_factory
        self.last_engine = None

    def run_pass(self, spec, pass_number):
        task = self.task_factory(spec, pass_number)
        context = self.context_factory(spec, pass_number)
        if not isinstance(task, TaskSpec) or not isinstance(context, ContextAssembly):
            raise ContractError("engine factories must return typed task and context objects")
        engine = self.router.select(task.capability)
        self.last_engine = (engine.name, engine.version)
        result = engine.execute(task, context)
        if not isinstance(result, EngineResult):
            raise ContractError("engine returned an invalid result")
        # Tools are proposals, not an authorization to execute them. Unknown usage
        # remains None so the controller's existing budget brake fails closed.
        return {"candidate": result.candidate, "tokens_used": result.token_usage,
                "provider": engine.name, "engine_name": engine.name,
                "engine_version": engine.version, "observations": []}
