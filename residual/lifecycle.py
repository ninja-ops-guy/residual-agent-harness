from __future__ import annotations
from collections import defaultdict
from threading import RLock
class ModuleLifecycleBus:
    def __init__(self): self._handlers=defaultdict(list); self._lock=RLock()
    def subscribe(self,event,handler):
        with self._lock:
            if handler not in self._handlers[event]: self._handlers[event].append(handler)
    def unsubscribe(self,event,handler):
        with self._lock:
            if handler in self._handlers.get(event,()): self._handlers[event].remove(handler)
    def emit(self,event,payload):
        with self._lock: handlers=tuple(self._handlers.get(event,()))+tuple(self._handlers.get("*",()))
        for handler in handlers:
            try: handler(event,dict(payload))
            except Exception: pass
