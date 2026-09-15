"""Independent original-main vs PR runtime-budget regression, no mocks."""
import dataclasses
import json
import subprocess
import sys
import types

from residual.sandbox import subprocess_backend as current
from residual.sandbox.spec import SandboxLimits, SandboxSpec


def test_declared_wall_budget_is_not_extended_for_unwrapped_payload():
    name = 'residual.sandbox._lane2_original_backend'
    original = types.ModuleType(name)
    original.__package__ = 'residual.sandbox'
    sys.modules[name] = original
    source = subprocess.check_output(
        ['git', 'show', 'a8082109:residual/sandbox/subprocess_backend.py'], text=True)
    exec(compile(source, '<baseline-a8082109>', 'exec'), vars(original))
    spec = SandboxSpec('lane2-deadline', limits=SandboxLimits(timeout_seconds=1))
    before = original.run_contained(['/bin/sleep', '2'], spec)
    after = current.run_contained(['/bin/sleep', '2'], spec)
    evidence = {'timeout_seconds': 1, 'payload': ['/bin/sleep', '2'],
                'baseline': dataclasses.asdict(before), 'reviewed': dataclasses.asdict(after)}
    print('TIMEOUT_CONTRACT', json.dumps(evidence))
    assert before.timed_out and not before.ok, 'baseline control did not exercise the deadline'
    assert after.timed_out and not after.ok, evidence
