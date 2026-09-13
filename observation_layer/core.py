"""Versioned observations with immutable JSON values and independently verifiable digests."""
from __future__ import annotations
import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass, field, fields
from enum import Enum


class ObservationKind(str, Enum):
    AGENT_SPAWNED = 'agent.spawned'
    AGENT_TERMINATED = 'agent.terminated'
    TOOL_INVOKED = 'tool.invoked'
    TOOL_COMPLETED = 'tool.completed'
    TOOL_FAILED = 'tool.failed'
    LLM_REQUEST = 'llm.request'
    LLM_RESPONSE = 'llm.response'
    LLM_FAILED = 'llm.failed'
    LLM_STREAM_CHUNK = 'llm.stream_chunk'
    STATE_TRANSITION = 'state.transition'
    HANDOFF = 'handoff'
    CHECKPOINT = 'checkpoint'
    CUSTOM = 'custom'


SCHEMA_VERSION = '1.1.0'


class FrozenDict(dict):
    def _readonly(self, *args, **kwargs):
        raise TypeError('Observation values are immutable')
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _readonly
    def __deepcopy__(self, memo):
        return self


def freeze(value):
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError('JSON keys must be strings')
        return FrozenDict((k, freeze(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError('Observation must contain finite JSON values')


@dataclass(frozen=True)
class Observation:
    obs_id: str
    trace_id: str
    kind: ObservationKind
    timestamp_ns: int
    schema_version: str
    prev_hash: str
    payload: dict
    tags: dict = field(default_factory=dict)
    source: str = 'unknown'
    digest: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'kind', ObservationKind(self.kind))
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError('Unsupported observation schema; legacy 1.0 traces need an explicit migration')
        if not all(isinstance(s, str) and 0 < len(s) <= 200 for s in (self.obs_id, self.trace_id, self.source)):
            raise ValueError('Invalid observation identity')
        if type(self.timestamp_ns) is not int or self.timestamp_ns < 0:
            raise ValueError('Invalid observation time')
        if not isinstance(self.payload, dict) or not isinstance(self.tags, dict) or any(not isinstance(v, str) for v in self.tags.values()):
            raise ValueError('Invalid observation payload or tags')
        if self.prev_hash != 'GENESIS' and (len(self.prev_hash) != 64 or any(c not in '0123456789abcdef' for c in self.prev_hash)):
            raise ValueError('Invalid previous digest')
        object.__setattr__(self, 'payload', freeze(self.payload))
        object.__setattr__(self, 'tags', freeze(self.tags))
        if len(self.canonical_bytes()) > 24000:
            raise ValueError('Observation exceeds 24 KB; reference an artifact instead')
        if not self.digest:
            object.__setattr__(self, 'digest', self.hash())

    def to_dict(self):
        return {f.name: self.kind.value if f.name == 'kind' else getattr(self, f.name) for f in fields(self)}

    def canonical_bytes(self):
        d = self.to_dict(); d.pop('digest')
        return json.dumps(d, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

    def hash(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


class ObservationSequencer:
    def __init__(self, trace_id, head_hash='GENESIS', count=0):
        self.trace_id, self._prev, self._count = trace_id, head_hash, count
    @property
    def count(self): return self._count
    @property
    def head_hash(self): return self._prev

    def draft(self, kind, payload, *, tags=None, source='unknown'):
        return Observation(str(uuid.uuid4()), self.trace_id, kind, time.time_ns(), SCHEMA_VERSION,
                           self._prev, payload, tags or {}, source)

    def commit(self, obs):
        # Filters may change content, but cannot change trace identity or linkage.
        d = obs.to_dict(); d.update(trace_id=self.trace_id, prev_hash=self._prev, digest='')
        sealed = Observation(**d)
        self._prev = sealed.digest; self._count += 1
        return sealed

    def next(self, kind, payload, *, tags=None, source='unknown'):
        return self.commit(self.draft(kind, payload, tags=tags, source=source))


def verify_chain(observations, *, expected_head=None, expected_count=None):
    """Detect modification, gaps, duplicates and reordering. Anchor head/count for truncation detection.

    A hash chain alone cannot authenticate an attacker-rewritten trace. Keep an
    independently trusted checkpoint for authenticity or tail-deletion detection.
    """
    prev, trace, seen, count = 'GENESIS', None, set(), 0
    try:
        for obs in observations:
            if obs.schema_version != SCHEMA_VERSION or obs.prev_hash != prev or obs.digest != obs.hash(): return False
            if obs.obs_id in seen or (trace is not None and trace != obs.trace_id): return False
            ObservationKind(obs.kind)
            seen.add(obs.obs_id); trace = obs.trace_id; prev = obs.digest; count += 1
    except (ValueError, TypeError, AttributeError):
        return False
    return (expected_head is None or prev == expected_head) and (expected_count is None or count == expected_count)
