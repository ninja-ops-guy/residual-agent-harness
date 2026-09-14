"""Explicit station opt-ins; default deployment remains dependency-free and offline."""
from __future__ import annotations
from residual.modules.adapters import HITLModule, LifecycleModule
from residual.tui import ObservationCollector, StationTUI
from .extensions import default_registry


class TerminalModule(LifecycleModule):
    name = 'terminal'

    def __init__(self, *, renderer=None):
        self.collector = ObservationCollector()
        self.tui = renderer or StationTUI(self.collector)

    def on_run_opened(self, spec):
        super().on_run_opened(spec)
        self.tui.start()

    def on_event(self, kind, payload):
        self.collector.on_event(kind,payload)

    def on_run_closed(self, result):
        self.tui.stop()


def deployment_extensions(*, hitl_gateway=None, tui=False):
    """Pass the returned factory to Station(root, extension_factory=...).

    The host supplies the same authenticated gateway/database used by the review
    service. A terminal subscribes to the actual extension observation stream.
    Each project gets its own registry; constructor-time freeze is unchanged.
    """
    def factory(station, project_id):
        registry = default_registry(station,project_id)
        if hitl_gateway is not None:
            registry.register_module(HITLModule(hitl_gateway))
        if tui:
            registry.register_module(TerminalModule())
        return registry
    return factory
