from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from common import (  # noqa: E402
    BASE_POLICY, EXPECTED_OUTPUT_COMMIT, PROMPTS, TASKS, apply_verified_delta,
    create_fixture, finalize, render_policy, verify_candidate,
)
from ai_providers.adapters.ollama_adapter import OllamaAdapter  # noqa: E402
from ai_providers.core import ChatRequest, Message, Role  # noqa: E402
from residual.core import canonical, strict_json  # noqa: E402
from residual.factory.eval_framework import FrozenWorkload, RunMeasurement  # noqa: E402


class OllamaWorker:
    def __init__(self, model: str, version: str, base_url: str, seed: int | None):
        self.model = model
        self.name = f'ollama:{model}'
        self.version = version
        self.seed = seed
        self.adapter = OllamaAdapter(base_url=base_url, timeout=300.0)

    def execute(self, task_id: str, baseline_source: str) -> tuple[str, int, float, float]:
        prompt = PROMPTS[task_id] + '\n\nCurrent service/policy.py:\n```python\n' + baseline_source + '\n```'
        started = time.monotonic()
        response = self.adapter.chat(ChatRequest(
            model=self.model,
            messages=(
                Message(Role.SYSTEM, 'You are running a measured benchmark. Return only the requested JSON object.'),
                Message(Role.USER, prompt),
            ),
            temperature=0,
            max_tokens=700,
            seed=self.seed,
            response_schema={
                'type': 'object',
                'properties': {'code': {'type': 'string'}},
                'required': ['code'],
                'additionalProperties': False,
            },
        ))
        elapsed = time.monotonic() - started
        payload = strict_json(response.content)
        if not isinstance(payload, dict) or set(payload) != {'code'} or not isinstance(payload['code'], str):
            raise ValueError('FB003 model output violated schema')
        usage = response.usage.get('total_tokens')
        if type(usage) is not int:
            raise ValueError('Ollama did not report token usage')
        raw = response.raw if isinstance(response.raw, dict) else {}
        gpu_ms = float(raw.get('eval_duration') or 0) / 1_000_000.0
        return payload['code'], usage, gpu_ms, elapsed


def _batch_width(config: str) -> int:
    if config == 'single':
        return 1
    if config == 'fixed':
        return 4
    if config == 'dynamic':
        return len(TASKS)
    raise ValueError('invalid config')


def main() -> int:
    p = argparse.ArgumentParser(description='Run one measured FB003 configuration against Ollama')
    p.add_argument('--config', choices=('single', 'fixed', 'dynamic'), required=True)
    p.add_argument('--run', type=int, required=True)
    p.add_argument('--workload', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--model-version', required=True)
    p.add_argument('--base-url', default='http://localhost:11434')
    args = p.parse_args()

    workload = FrozenWorkload.from_dict(strict_json(Path(args.workload).read_text(encoding='utf-8')))
    worker = OllamaWorker(args.model, args.model_version, args.base_url, workload.seed)
    if (worker.name, worker.version) != (workload.engine_name, workload.engine_version):
        raise SystemExit('frozen model identity does not match runner')

    started = time.monotonic()
    token_total = 0
    gpu_ms_total = 0.0
    coordination_s = 0.0
    verifier_total = 0
    verifier_rejected = 0
    conflict_excess = 0
    resolution_groups = 0
    peak_workers = 1
    current_policy = deepcopy(BASE_POLICY)
    remaining = list(TASKS)
    task_evidence = {}

    with tempfile.TemporaryDirectory(prefix=f'residual-fb003-{args.config}-{args.run}-') as td:
        repo = Path(td) / 'repo'
        input_commit, _ = create_fixture(repo)
        if input_commit != workload.input_commit:
            raise SystemExit('fixture input commit does not match frozen workload')

        width = _batch_width(args.config)
        while remaining:
            batch = remaining[:width]
            del remaining[:len(batch)]
            baseline = deepcopy(current_policy)
            baseline_source = render_policy(baseline)
            peak_workers = max(peak_workers, len(batch))
            with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                futures = {task_id: pool.submit(worker.execute, task_id, baseline_source) for task_id in batch}
                results = {task_id: future.result() for task_id, future in futures.items()}

            coord_started = time.monotonic()
            verified = []
            for task_id in batch:
                source, tokens, gpu_ms, model_elapsed = results[task_id]
                verifier_total += 1
                if not verify_candidate(task_id, source, baseline):
                    verifier_rejected += 1
                    raise ValueError(f'FB003 candidate rejected: {task_id}')
                verified.append(task_id)
                token_total += tokens
                gpu_ms_total += gpu_ms
                task_evidence[task_id] = {
                    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                    'tokens': tokens,
                    'model_elapsed_s': model_elapsed,
                }

            if len(verified) > 1:
                # Every verified candidate is a complete edit of the same file from
                # the same base. One can be applied directly; each additional edit
                # is integration conflict work requiring the frozen resolution rule.
                conflict_excess += len(verified) - 1
                resolution_groups += 1
            for task_id in verified:
                apply_verified_delta(current_policy, task_id)
            coordination_s += time.monotonic() - coord_started

        coord_started = time.monotonic()
        commit, passed, total = finalize(repo, current_policy)
        coordination_s += time.monotonic() - coord_started
        if commit != EXPECTED_OUTPUT_COMMIT:
            raise ValueError('FB003 final output commit drift')

    elapsed_s = time.monotonic() - started
    digest = hashlib.sha256(canonical({
        'benchmark': 'FB003',
        'config': args.config,
        'run_index': args.run,
        'engine': [worker.name, worker.version],
        'tasks': task_evidence,
        'conflict_excess': conflict_excess,
        'resolution_groups': resolution_groups,
        'peak_workers': peak_workers,
        'output_commit': commit,
    }).encode()).hexdigest()

    measurement = RunMeasurement(
        config=args.config,
        run_index=args.run,
        elapsed_time_minutes=elapsed_s / 60.0,
        accepted_tasks=len(TASKS),
        token_cost_total=token_total,
        gpu_time_minutes=gpu_ms_total / 60000.0,
        coordination_time_minutes=coordination_s / 60.0,
        rework_tasks=conflict_excess,
        merge_conflicts=conflict_excess,
        verifier_rejected=verifier_rejected,
        verifier_total=verifier_total,
        final_tests_passed=passed,
        final_tests_total=total,
        api_cost_usd=0.0,
        gpu_cost_usd=0.0,
        infrastructure_cost_usd=0.0,
        engine_name=worker.name,
        engine_version=worker.version,
        output_commit=commit,
        observation_digest=digest,
        simulation=False,
        peak_workers=peak_workers,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = measurement.to_dict()
    payload['fb003_resolution_groups'] = resolution_groups
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
