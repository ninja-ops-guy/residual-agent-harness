from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from common import EXPECTED_OUTPUT_COMMIT, INPUT_COMMIT, TASKS, create_fixture  # noqa: E402
from residual.factory.evidence_receipts import StationIdentity  # noqa: E402


def _ollama_version(base_url: str, model: str) -> str:
    with urllib.request.urlopen(base_url.rstrip('/') + '/api/tags', timeout=10) as response:
        payload = json.load(response)
    for item in payload.get('models', []):
        if item.get('name') == model or item.get('model') == model:
            digest = item.get('digest')
            if isinstance(digest, str) and digest:
                return digest
    raise SystemExit(f'model {model!r} is not installed at {base_url}')


def main() -> int:
    p = argparse.ArgumentParser(description='Prepare Frozen Benchmark 003 for a local Ollama model')
    p.add_argument('--model', required=True)
    p.add_argument('--base-url', default='http://localhost:11434')
    p.add_argument('--output', default=str(HERE / 'workload.local.json'))
    p.add_argument('--station-key', default=str(HERE / 'station.local.pem'))
    args = p.parse_args()

    fixture = HERE / '.fixture-check'
    if fixture.exists():
        raise SystemExit(f'remove stale {fixture} before preparing FB003')
    try:
        input_commit, output_commit = create_fixture(fixture, known_good=True)
        assert input_commit == INPUT_COMMIT and output_commit == EXPECTED_OUTPUT_COMMIT
    finally:
        shutil.rmtree(fixture, ignore_errors=True)

    version = _ollama_version(args.base_url, args.model)
    ids = tuple(TASKS)
    workload = {
        'schema_version': 'factory-evaluation-v1',
        'workload_id': 'fb003-shared-edit-conflicts',
        'requirements': [f'FB003-{x.upper()}' for x in ids],
        'tasks': [
            {'task_id': x, 'requirement_ids': [f'FB003-{x.upper()}'], 'depends_on': [],
             'acceptance': [f'bounded-shared-edit:{x}']} for x in ids
        ],
        'input_commit': INPUT_COMMIT,
        'expected_output_commit': EXPECTED_OUTPUT_COMMIT,
        'engine': {'name': f'ollama:{args.model}', 'version': version, 'temperature': 0, 'seed': 7},
        'driver_argv': [
            sys.executable, str(HERE / 'run_live.py'),
            '--config', '{config}', '--run', '{run}', '--workload', '{workload}', '--output', '{output}',
            '--model', args.model, '--model-version', version, '--base-url', args.base_url,
        ],
    }
    Path(args.output).write_text(json.dumps(workload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    key = Path(args.station_key)
    if not key.exists():
        StationIdentity.generate().save_private(key)
    print(json.dumps({'workload': str(Path(args.output).resolve()), 'station_key': str(key.resolve()),
                      'model_version': version}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
