"""Scripted M2 execution demo: real isolation and Git, no model or receipt claims.

Run from the repository root:
    python examples/factory/brokered_worker_demo.py --output /tmp/residual-m2-demo
The output directory must not already exist. Linux + libseccomp.so.2 are required.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from residual.factory import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from residual.factory.runtime import FactoryRuntime
from residual.factory.runtime_journal import RuntimeJournal
from residual.factory.runtime_workspace import git
from residual.factory.worker_contract import WorkerContract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.output).absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    repository = root / 'repository'
    repository.mkdir()
    git(repository, 'init')
    (repository / 'numbers.json').write_text('[1,2,3]\n')
    git(repository, 'add', '.')
    git(repository, '-c', 'user.name=Residual Demo', '-c', 'user.email=demo@localhost', 'commit', '-m', 'fixture input')
    commit = git(repository, 'rev-parse', 'HEAD').decode().strip()
    plan = ExecutionPlan('Sum the declared fixture numbers',
                         (Requirement('REQ-1', 'Write their sum', ('sum-check',)),),
                         (FactoryTask('sum', 'Produce total.txt', ('REQ-1',), swarm='math'),))
    approval = FrozenPlan.approve(plan, 'local-demo-operator')
    contract = WorkerContract(
        task_id='sum', worker_id='worker-1', swarm_id='math', execution_plan_hash=plan.graph_hash,
        attempt_id='attempt-1', lease_id='lease-1', lease_generation=1, input_commit=commit,
        workspace_root=str(root / 'work' / 'math' / 'attempt-1'), inputs=('numbers.json',),
        allowed_outputs=('total.txt',), forbidden=(), requirements=('REQ-1',), acceptance=('sum-check',),
        dependencies=(), allowed_tools=('read_file', 'write_file'), forbidden_tools=('shell',),
        token_budget=0, wall_clock_budget_s=5, max_tool_calls=4, max_file_writes=1, memory_limit_mb=128)
    journal = RuntimeJournal(root / 'state' / 'journal.db', trace_id='m2-scripted-demo')
    runtime = FactoryRuntime(repository, root / 'work', journal, allow_local_worker_code=True)
    source = "import json\nwrite_file('total.txt',str(sum(json.loads(read_file('numbers.json')))))"
    result = runtime.run(plan, approval, contract, source)
    for name, value in [('plan', plan.to_dict()), ('approval', approval.to_dict()),
                        ('contract', contract.to_dict()), ('result', result.to_dict())]:
        (root / f'{name}.json').write_text(json.dumps(value, indent=2) + '\n')
    journal.export_jsonl(root / 'observations.jsonl')
    print(json.dumps({'status': result.status, 'output': str(root),
                      'model_used': False, 'station_verified': False,
                      'source_branch_unchanged': git(repository, 'rev-parse', 'HEAD').decode().strip() == commit}))
    return 0 if result.status == 'CANDIDATE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
