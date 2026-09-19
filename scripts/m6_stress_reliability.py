from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import tempfile
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station

SPEC = r"""# M6 ImprovementSpec repeated reliability trial

Implement one new RESIDUAL module: `residual/improvement/spec.py`.

Requirements:
1. Define an immutable/frozen `ImprovementSpec` dataclass with exactly these fields:
   - improvement_id: str
   - observation: str
   - hypothesis: str
   - target_metrics: tuple[str, ...]
   - preserve_metrics: tuple[str, ...]
   - protected_invariants: tuple[str, ...]
   - acceptance: dict[str, object]
   - human_approval_required: bool = True
2. `__post_init__` MUST reject blank improvement_id, observation, or hypothesis; empty target_metrics, preserve_metrics, or protected_invariants; any blank metric/invariant entry; empty acceptance; and human_approval_required=False. Rejection MUST raise ValueError.
3. Provide `to_dict()` returning a JSON-serializable dictionary. Tuple fields serialize as lists. The acceptance mapping MUST be copied so callers cannot mutate internal state through the returned dictionary.
4. Provide `canonical_json()` returning deterministic compact JSON with sorted keys.
5. Provide `sha256()` returning lowercase SHA-256 hex digest of UTF-8 canonical_json().
6. No network, subprocess, filesystem, model/provider, Git, verifier, M4, receipt, or promotion operations are allowed in this module.
7. Keep the implementation small and dependency-free beyond the Python standard library.
"""

CHECK = r"""import hashlib,json
from residual.improvement.spec import ImprovementSpec
kw=dict(
 improvement_id='RI-0001',
 observation='retry cost is high',
 hypothesis='bounded retry reduces cost',
 target_metrics=('token_cost',),
 preserve_metrics=('task_success',),
 protected_invariants=('M4', 'evidence_integrity'),
 acceptance={'token_reduction_pct': 10, 'max_success_regression_pct': 1},
)
s=ImprovementSpec(**kw)
d=s.to_dict()
assert d['target_metrics']==['token_cost']
assert d['preserve_metrics']==['task_success']
assert d['protected_invariants']==['M4','evidence_integrity']
assert d['human_approval_required'] is True
d['acceptance']['token_reduction_pct']=999
assert s.to_dict()['acceptance']['token_reduction_pct']==10
c=s.canonical_json()
assert c==json.dumps(s.to_dict(),sort_keys=True,separators=(',',':'),ensure_ascii=False)
assert s.sha256()==hashlib.sha256(c.encode('utf-8')).hexdigest()
assert s.sha256()==ImprovementSpec(**kw).sha256()
bad=[
 dict(kw, improvement_id=' '),
 dict(kw, observation=''),
 dict(kw, hypothesis=''),
 dict(kw, target_metrics=()),
 dict(kw, preserve_metrics=()),
 dict(kw, protected_invariants=()),
 dict(kw, target_metrics=('ok',' ')),
 dict(kw, acceptance={}),
 dict(kw, human_approval_required=False),
]
for case in bad:
 try: ImprovementSpec(**case)
 except ValueError: pass
 else: raise AssertionError('invalid ImprovementSpec accepted: '+repr(case))
"""

MANIFEST = {
    "schema_version": 1,
    "name": "M6 ImprovementSpec Reliability Trial",
    "goal": "Implement the bounded recursive-improvement contract under frozen acceptance rules.",
    "tasks": [{
        "id": "M6-REPEAT-001",
        "title": "Implement ImprovementSpec",
        "instruction": SPEC,
        "files": ["residual/improvement/spec.py"],
        "context": [],
        "depends_on": [],
        "route": "local",
        "checks": [
            {"kind": "python_compile", "path": "residual/improvement/spec.py"},
            {"kind": "command", "argv": ["{python}", "-c", CHECK], "timeout": 30},
        ],
    }],
}


def run_trial(model: str, trial: int) -> dict:
    mission = "# M6 repeated reliability trial\n\n" + SPEC + "\n\n```json\n" + json.dumps(MANIFEST, indent=2) + "\n```\n"
    with tempfile.TemporaryDirectory(prefix=f"residual-m6-repeat-{trial}-") as root:
        station = Station(root)
        save_settings(station.store, {
            "local": {"kind": "ollama", "model": model, "base_url": "http://127.0.0.1:11434", "output_token_field": "max_tokens"},
            "review_placement": "local",
            "workers": 1,
            "max_output_tokens": 1600,
            "batch_max_passes": 5,
            "batch_token_budget": 30000,
            "batch_wall_clock_s": 900,
        })
        pid = station.create(mission, commands=True)["project_id"]
        result = station.batch(pid)
        project = station.store.project(pid)
        task = project["tasks"][0]
        ev = station.store.events(pid, 0, 100000)
        success = (
            result["integrated"] == 1
            and task["state"] == "integrated"
            and all(c.get("passed") is True for c in task["checks_result"])
            and task.get("review", {}).get("approved") is True
            and bool(task.get("verification_receipt"))
        )
        failure_classes = []
        for e in ev:
            if e["event_type"] == "task.transition" and e["data"].get("to") == "repair_required":
                failure_classes.extend(e["data"].get("findings", []))
        return {
            "trial": trial,
            "success": success,
            "batch": result,
            "metrics": station.metrics(pid),
            "task": {k: task.get(k) for k in ("state","attempt","findings","checks_result","review","head_commit","checks_hash","verification_receipt")},
            "failure_classes": failure_classes,
            "events": ev,
        }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--output", default="runs/m6-stress-reliability/evidence.json")
    a = p.parse_args()
    if a.trials < 1 or a.trials > 5:
        raise SystemExit("trials must be 1..5")
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    trials = [run_trial(a.model, i) for i in range(1, a.trials + 1)]
    data = {
        "schema_version": 1,
        "campaign": "M6-STRESS-A",
        "experiment": "STRESS-A6-reliability",
        "baseline_sha": "699e2869e294fe157b4bfd73a272057683a2f7e0",
        "spec_sha256": hashlib.sha256(SPEC.encode()).hexdigest(),
        "model": a.model,
        "environment": {"python": sys.version, "platform": platform.platform()},
        "trials": trials,
        "summary": {
            "trials": len(trials),
            "successes": sum(1 for t in trials if t["success"]),
            "accepted_rate": sum(1 for t in trials if t["success"]) / len(trials),
            "total_calls": sum(t["metrics"]["calls"] for t in trials),
            "total_reported_tokens": sum(t["metrics"]["reported_tokens"] for t in trials),
            "total_wall_clock_s": sum(t["batch"]["control"]["wall_clock_s"] for t in trials),
        },
    }
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("STRESS_RELIABILITY_EVIDENCE=" + json.dumps(data, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
