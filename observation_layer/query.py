"""
observation_layer.query
=======================
Read-side: replay, chain verification, and lightweight analytics over
stored observations. Works on any iterable of Observation objects —
from InMemorySink, or by parsing JSONL back into Observations.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .core import Observation, ObservationKind, verify_chain


def load_jsonl(path: str | Path) -> Iterator[Observation]:
    """Strict replay: malformed or unsealed records are evidence failures, never skipped."""
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            if not line.strip(): continue
            try:
                def pairs(items):
                    result = {}
                    for k, v in items:
                        if k in result: raise ValueError("Duplicate observation key")
                        result[k] = v
                    return result
                d = json.loads(line, object_pairs_hook=pairs)
                if not d.get("digest"): raise ValueError("Missing digest")
                yield Observation(**d)
            except (ValueError, TypeError, KeyError, AttributeError):
                raise ValueError(f"Invalid observation at line {number}") from None


def replay(path: str | Path, verify: bool = True) -> list[Observation]:
    """Load and optionally verify a trace file."""
    events = list(load_jsonl(path))
    if verify and events:
        if not verify_chain(events):
            raise ValueError(f"chain verification failed for {path}")
    return events


def filter_events(
    events: Iterable[Observation],
    *,
    kind: Optional[str] = None,
    tag_key: Optional[str] = None,
    tag_value: Optional[str] = None,
    source: Optional[str] = None,
) -> Iterator[Observation]:
    for e in events:
        if kind is not None and e.kind.value != kind:
            continue
        if tag_key is not None and e.tags.get(tag_key) != tag_value:
            continue
        if source is not None and e.source != source:
            continue
        yield e


def latency_summary(events: Iterable[Observation], kind: str = ObservationKind.TOOL_COMPLETED.value) -> dict:
    """Duration stats for a given event kind, keyed by the 'tool' or 'model' tag."""
    buckets: dict[str, list[float]] = defaultdict(list)
    for e in filter_events(events, kind=kind):
        key = e.tags.get("tool") or e.tags.get("model") or "unknown"
        if "duration_ms" in e.payload:
            buckets[key].append(float(e.payload["duration_ms"]))
    out = {}
    for k, v in buckets.items():
        v_sorted = sorted(v)
        n = len(v_sorted)
        out[k] = {
            "n": n,
            "mean_ms": round(sum(v_sorted) / n, 3),
            "p50_ms": round(v_sorted[n // 2], 3),
            "p95_ms": round(v_sorted[int(n * 0.95)], 3) if n >= 20 else None,
            "max_ms": round(v_sorted[-1], 3),
        }
    return out


def error_rate(events: Iterable[Observation]) -> dict:
    """Failed / (completed + failed) per tool."""
    events = list(events)
    completed = Counter(e.tags.get("tool", "?") for e in filter_events(events, kind=ObservationKind.TOOL_COMPLETED.value))
    failed = Counter(e.tags.get("tool", "?") for e in filter_events(events, kind=ObservationKind.TOOL_FAILED.value))
    tools = set(completed) | set(failed)
    return {
        t: {"failed": failed[t], "completed": completed[t], "error_rate": round(failed[t] / max(1, failed[t] + completed[t]), 4)}
        for t in tools
    }


def event_counts(events: Iterable[Observation]) -> Counter:
    return Counter(e.kind.value for e in events)


def trace_timeline(events: Iterable[Observation]) -> list[tuple[int, str, str]]:
    """(timestamp_ns, kind, one-line summary) sorted for human reading."""
    timeline = []
    for e in sorted(events, key=lambda x: x.timestamp_ns):
        summary = e.payload.get("tool") or e.payload.get("model") or e.payload.get("agent_id") or ""
        timeline.append((e.timestamp_ns, e.kind.value, str(summary)))
    return timeline
