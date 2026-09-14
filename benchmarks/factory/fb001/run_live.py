from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from common import EXPECTED, EXPECTED_OUTPUT_COMMIT, PROMPTS, create_fixture, write_policy  # noqa: E402
from ai_providers.adapters.ollama_adapter import OllamaAdapter  # noqa: E402
from ai_providers.core import ChatRequest, Message, Role  # noqa: E402
from residual.core import strict_json  # noqa: E402
from residual.engines.protocol import ContextAssembly, EngineHealth, EngineResult, TaskSpec  # noqa: E402
from residual.factory.eval_driver import EngineBackedEvaluationDriver, FinalizedRun  # noqa: E402
from residual.factory.eval_framework import FrozenWorkload  # noqa: E402


class FB001OllamaEngine:
    capability_class = "agent"
    locality = "local"

    def __init__(self, model: str, version: str, base_url: str, seed: int | None):
        self.model = model
        self.name = f"ollama:{model}"
        self.version = version
        self.seed = seed
        self.adapter = OllamaAdapter(base_url=base_url, timeout=300.0)

    def supports(self, capability: str) -> bool:
        return capability == "agent"

    def health(self) -> EngineHealth:
        return EngineHealth.HEALTHY

    def normalize(self, raw_output) -> EngineResult:
        return raw_output if isinstance(raw_output, EngineResult) else EngineResult(candidate=raw_output)

    def execute(self, task: TaskSpec, context: ContextAssembly) -> EngineResult:
        if task.task_id not in PROMPTS:
            raise ValueError("unknown FB001 task")
        request = ChatRequest(
            model=self.model,
            messages=(
                Message(Role.SYSTEM, "You are executing a deterministic benchmark. Follow the requested JSON shape exactly."),
                Message(Role.USER, PROMPTS[task.task_id]),
            ),
            temperature=0,
            max_tokens=128,
            seed=self.seed,
            response_schema={
                "type": "object",
                "properties": {"value": {}},
                "required": ["value"],
                "additionalProperties": False,
            },
        )
        response = self.adapter.chat(request)
        payload = strict_json(response.content)
        if not isinstance(payload, dict) or set(payload) != {"value"}:
            raise ValueError("FB001 model output violated schema")
        usage = response.usage.get("total_tokens")
        if type(usage) is not int:
            raise ValueError("Ollama did not report token usage")
        raw = response.raw if isinstance(response.raw, dict) else {}
        metadata = {
            "provenance": "measured",
            "provider": "ollama",
            "model": response.model,
            "prompt_tokens": response.usage.get("prompt_tokens"),
            "completion_tokens": response.usage.get("completion_tokens"),
            "ollama_total_duration_ns": raw.get("total_duration"),
            "ollama_eval_duration_ns": raw.get("eval_duration"),
        }
        return EngineResult(
            candidate=payload["value"],
            token_usage=usage,
            wall_clock_ms=int((raw.get("total_duration") or 0) / 1_000_000),
            raw_metadata=metadata,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute one measured FB001 configuration/run against Ollama")
    parser.add_argument("--config", choices=("single", "fixed", "dynamic"), required=True)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args()

    workload = FrozenWorkload.from_dict(strict_json(Path(args.workload).read_text(encoding="utf-8")))
    engine = FB001OllamaEngine(args.model, args.model_version, args.base_url, workload.seed)
    if (engine.name, engine.version) != (workload.engine_name, workload.engine_version):
        raise SystemExit("frozen model identity does not match runner")

    with tempfile.TemporaryDirectory(prefix=f"residual-fb001-{args.config}-{args.run}-") as td:
        repo = Path(td) / "repo"
        input_commit, _ = create_fixture(repo, known_good=False)
        if input_commit != workload.input_commit:
            raise SystemExit("fixture input commit does not match frozen workload")

        def verifier(task_id: str, _acceptance: tuple[str, ...], candidate) -> bool:
            return candidate == EXPECTED[task_id]

        def finalizer(_workload, outputs, _config, _run_index) -> FinalizedRun:
            commit = write_policy(repo, dict(outputs))
            if commit != EXPECTED_OUTPUT_COMMIT:
                raise ValueError("final output commit drift")
            policy = strict_json((repo / "policy.json").read_text(encoding="utf-8"))
            checks = [commit == _workload.expected_output_commit, policy.get("schema") == "service-policy-v1"]
            return FinalizedRun(commit, sum(bool(x) for x in checks), len(checks), 0)

        driver = EngineBackedEvaluationDriver(
            engine,
            finalizer=finalizer,
            verifier=verifier,
            fixed_workers=4,
            max_workers=6,
        )
        measurement = driver.run(workload, args.config, args.run, lambda _event: None)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(measurement.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
