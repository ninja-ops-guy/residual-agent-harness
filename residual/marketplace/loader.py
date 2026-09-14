from __future__ import annotations
from importlib.metadata import entry_points
def discover_modules(group="residual.modules"):
    eps=entry_points(); selected=eps.select(group=group) if hasattr(eps,"select") else eps.get(group,()); return tuple(sorted(selected,key=lambda e:e.name))
def load_modules(group="residual.modules"): return tuple(ep.load()() for ep in discover_modules(group))
