"""Tests for FrozenWorkload manifest immutability and content addressing."""
import json

import pytest

from residual.eval import FrozenWorkload, WorkloadTask


def _tasks(n=4):
    return tuple(
        WorkloadTask(task_id=f"t-{i}", kind="netops", prompt=f"task {i}",
                     expected={"ok": True}, metadata={"i": i})
        for i in range(n)
    )


def test_manifest_is_content_addressed_and_stable():
    wl1 = FrozenWorkload(name="w", tasks=_tasks(), seed=7)
    wl2 = FrozenWorkload(name="w", tasks=_tasks(), seed=7)
    assert wl1.manifest_hash == wl2.manifest_hash
    assert len(wl1.manifest_hash) == 64
    assert wl1.verify()
    assert wl1.manifest()["task_count"] == 4


def test_manifest_changes_with_content():
    a = FrozenWorkload(name="w", tasks=_tasks(), seed=7)
    b = FrozenWorkload(name="w", tasks=_tasks()[:-1], seed=7)
    c = FrozenWorkload(name="w2", tasks=_tasks(), seed=7)
    d = FrozenWorkload(name="w", tasks=_tasks(), seed=8)
    assert a.manifest_hash != b.manifest_hash
    assert a.manifest_hash != c.manifest_hash
    assert a.manifest_hash != d.manifest_hash


def test_workload_is_frozen():
    wl = FrozenWorkload(name="w", tasks=_tasks(), seed=7)
    with pytest.raises(AttributeError):
        wl.name = "tampered"  # noqa: B010 — attribute assignment on frozen object
    with pytest.raises(AttributeError):
        wl.tasks = ()  # noqa: B010
    task = wl.tasks[0]
    with pytest.raises(Exception):
        object.__setattr__  # frozen dataclass raises FrozenInstanceError
        task.prompt = "evil"


def test_empty_workload_rejected():
    with pytest.raises(ValueError):
        FrozenWorkload(name="w", tasks=(), seed=7)


def test_serialization_roundtrip():
    wl = FrozenWorkload.standard(cases=6)
    loaded = FrozenWorkload.from_json(wl.to_json())
    assert loaded.manifest_hash == wl.manifest_hash
    assert loaded.verify()


def test_tampered_task_detected_on_load():
    wl = FrozenWorkload.standard(cases=6)
    data = wl.to_dict()
    data["tasks"][0]["prompt"] = "tampered prompt"
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        FrozenWorkload.from_dict(data)


def test_tampered_manifest_hash_detected():
    wl = FrozenWorkload.standard(cases=6)
    data = wl.to_dict()
    data["manifest"]["manifest_hash"] = "0" * 64
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        FrozenWorkload.from_dict(data)


def test_reordered_tasks_detected():
    wl = FrozenWorkload.standard(cases=6)
    data = wl.to_dict()
    data["tasks"] = list(reversed(data["tasks"]))
    with pytest.raises(ValueError):
        FrozenWorkload.from_dict(data)


def test_unsupported_schema_rejected():
    wl = FrozenWorkload.standard(cases=2)
    data = json.loads(wl.to_json())
    data["manifest"]["schema_version"] = "bogus"
    with pytest.raises(ValueError, match="unsupported workload schema"):
        FrozenWorkload.from_dict(data)


def test_standard_suite_deterministic():
    assert FrozenWorkload.standard().manifest_hash == FrozenWorkload.standard().manifest_hash
