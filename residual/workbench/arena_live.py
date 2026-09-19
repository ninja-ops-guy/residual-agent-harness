"""Bounded live executor for frozen AX-ARENA protocols.

The executor is deliberately narrow: exact-answer tasks, one raw Arena control
call, and the same Arena model behind RESIDUAL's real obligation harness. It is
an apparatus for matched-model harness experiments, not a general coding-agent
benchmark. More complex workloads should provide their own task/evaluator
adapter while preserving the same frozen schedule and trace contract.
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from ai_providers import ChatRequest, ChatResponse, Message, ProviderError, Role
from ai_providers.adapters.arena_adapter import ArenaAdapter, ARENA_DEFAULT_BASE_URL

from ..core import ContractError, Obligation, Registry, Task, Verdict, canonical, digest
from ..engine import Harness, Limits
from ..eval.arena import AgentEvaluationTrace, ArenaTraceEvent
from ..eval_frozen.workload import workload_from_json
from ..modular import ModularProvider
from ..study import sources

CONTROL_SYSTEM = (
    "Answer the task directly. Return only the final answer with no explanation, "
    "prefix, suffix, markdown, or reasoning transcript."
)


def _append_jsonl(path: Path, value) -> None:
    line = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


def _write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")


def _answer_ok(value, expected: str) -> bool:
    return isinstance(value, str) and value.strip() == expected.strip()


def _base_trace(
    *,
    lock,
    job,
    task,
    environment_digest,
    harness_version,
    events,
    usage,
    verdict,
    provider_metadata,
):
    return AgentEvaluationTrace.build(
        experiment_id=job["experiment_id"],
        observation_id=job["observation_id"],
        task_id=job["task_id"],
        condition=job["condition"],
        model=job["model"],
        harness_version=harness_version,
        environment_digest=environment_digest,
        available_tools=(),
        events=events,
        usage=usage,
        verdict=verdict,
        provider_metadata=provider_metadata,
    )


def _control(lock, job, task, environment_digest, api_key, base_url, max_output_tokens):
    model_id = job["model"].removeprefix("arena:")
    adapter = ArenaAdapter(api_key=api_key, base_url=base_url)
    req = ChatRequest(
        model=model_id,
        messages=(
            Message(Role.SYSTEM, CONTROL_SYSTEM),
            Message(Role.USER, task.prompt),
        ),
        temperature=0.0,
        max_tokens=max_output_tokens,
    )
    events = [ArenaTraceEvent.build(0, "model_call", {
        "provider": "arena",
        "role": "control",
        "requested_model": model_id,
    })]
    metadata = {
        "provider": "arena",
        "fallback_used": False,
        "requested_model": model_id,
    }
    try:
        response = adapter.chat(req)
    except ProviderError as exc:
        events.append(ArenaTraceEvent.build(1, "provider_error", exc.to_dict()))
        return _base_trace(
            lock=lock, job=job, task=task, environment_digest=environment_digest,
            harness_version="minimal-arena-control-v1",
            events=tuple(events), usage={},
            verdict={"state": "UNKNOWN", "verified_task_success": None,
                     "reason": "provider_error"},
            provider_metadata=metadata,
        )

    metadata["resolved_model"] = response.model
    answer = response.content.strip()
    success = _answer_ok(answer, task.expected)
    events.append(ArenaTraceEvent.build(1, "evaluation", {
        "state": "PASS" if success else "FAIL",
        "answer_sha256": digest(answer),
    }))
    usage = dict(response.usage)
    return _base_trace(
        lock=lock, job=job, task=task, environment_digest=environment_digest,
        harness_version="minimal-arena-control-v1",
        events=tuple(events), usage=usage,
        verdict={"state": "PASS" if success else "FAIL",
                 "verified_task_success": success},
        provider_metadata=metadata,
    )


def _residual(lock, job, task, environment_digest, api_key, base_url,
              max_output_tokens, residual_rounds):
    model_id = job["model"].removeprefix("arena:")
    registry = Registry()

    # Expected output is captured only by trusted verifier code. It is not
    # placed in the Task, Obligation parameters, model packet, or evidence.
    expected = task.expected

    def exact_answer(value, _context):
        if not isinstance(value, str):
            return Verdict.fail("arena_answer_type", "Return the final answer as a JSON string.")
        return (Verdict.passed() if _answer_ok(value, expected)
                else Verdict.fail("arena_answer_mismatch", "Revise the proposed final answer."))

    registry.check("arena_exact", exact_answer, "1")
    obligation = Obligation(
        id="answer",
        instruction=(
            "Solve the stated task. Return only the final answer as the value "
            "for obligation 'answer'; do not include an explanation."
        ),
        check="arena_exact",
        cloud=True,
    )
    residual_task = Task(
        id=task.task_id,
        goal=task.prompt,
        artifacts={},
        obligations=(obligation,),
    )
    provider = ModularProvider(
        {
            "kind": "arena",
            "model": model_id,
            "base_url": base_url,
            "placement": "remote",
            "output_token_field": "max_completion_tokens",
        },
        key=api_key,
    )
    limits = Limits(
        local_rounds=0,
        expert_rounds=residual_rounds,
        max_calls=residual_rounds,
        max_expert_calls=residual_rounds,
        max_remote_input_bytes=500_000,
        max_request_bytes=200_000,
        max_output_tokens=max_output_tokens,
        max_requested_lines=1,
        seed_lines=0,
    )
    harness = Harness(registry, None, provider, limits, None, "residual")
    result = harness.run(residual_task)

    events = []
    for call in harness.calls:
        events.append(ArenaTraceEvent.build(len(events), "model_call", {
            "provider": "arena",
            "role": call["role"],
            "request_bytes": call["request_bytes"],
            "error": call["error"],
        }))

    answer = result["values"].get("answer")
    unresolved = result["unresolved"].get("answer", {})
    code = unresolved.get("code") if isinstance(unresolved, dict) else None
    if answer is not None:
        success = _answer_ok(answer, expected)
        state = "PASS" if success else "FAIL"
        reason = None
    elif code == "provider_exception":
        success = None
        state = "UNKNOWN"
        reason = "provider_error"
    else:
        success = False
        state = "FAIL"
        reason = code or "no_verified_answer"

    events.append(ArenaTraceEvent.build(len(events), "evaluation", {
        "state": state,
        "reason": reason,
        "answer_sha256": digest(answer) if isinstance(answer, str) else None,
        "controller_status": result["status"],
    }))
    metrics = result["metrics"]
    usage = {}
    if metrics["remote_usage_complete"]:
        usage = {
            "prompt_tokens": metrics["remote_input_tokens_reported"],
            "completion_tokens": metrics["remote_output_tokens_reported"],
            "total_tokens": (
                metrics["remote_input_tokens_reported"]
                + metrics["remote_output_tokens_reported"]
            ),
        }
    metadata = {
        "provider": "arena",
        "fallback_used": False,
        "requested_model": model_id,
        "provider_calls": len(harness.calls),
    }
    engine_hash = lock["source_hashes"].get("residual/engine.py", "")[:16]
    return _base_trace(
        lock=lock, job=job, task=task, environment_digest=environment_digest,
        harness_version="residual-obligation-harness-" + (engine_hash or "unknown"),
        events=tuple(events), usage=usage,
        verdict={"state": state, "verified_task_success": success,
                 **({"reason": reason} if reason else {})},
        provider_metadata=metadata,
    )


def run_protocol(lock, output: Path, *, max_output_tokens=256, residual_rounds=2):
    """Execute every frozen schedule cell and durably append one trace per cell."""
    if lock.get("evidence_level") != "live_model":
        raise ContractError("AX-ARENA live runner requires evidence_level=live_model")
    if lock.get("source_hashes") != sources():
        raise ContractError("AX-ARENA source tree changed after protocol freeze")
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 8192:
        raise ContractError("AX-ARENA max output tokens must be 1..8192")
    if type(residual_rounds) is not int or not 1 <= residual_rounds <= 8:
        raise ContractError("AX-ARENA residual rounds must be 1..8")

    api_key = os.environ.get("ARENA_API_KEY")
    if not api_key:
        raise ContractError("ARENA_API_KEY is required for AX-ARENA live execution")
    base_url = os.environ.get("ARENA_BASE_URL", ARENA_DEFAULT_BASE_URL)

    workload = workload_from_json(canonical(lock["workload"]))
    tasks = {task.task_id: task for task in workload.slice_tasks(lock["slice"])}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)

    environment = {
        "protocol_sha256": lock["sha256"],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "arena_base_url": base_url,
        "max_output_tokens": max_output_tokens,
        "residual_rounds": residual_rounds,
    }
    environment_digest = digest(environment)
    environment["sha256"] = environment_digest
    _write_json(output / "protocol.json", lock)
    _write_json(output / "environment.json", environment)

    traces = []
    for job in lock["schedule"]:
        task = tasks.get(job["task_id"])
        if task is None:
            raise ContractError("AX-ARENA scheduled task absent from frozen workload")
        if job["condition"] == "control":
            trace = _control(
                lock, job, task, environment_digest, api_key, base_url,
                max_output_tokens,
            )
        elif job["condition"] == "residual":
            trace = _residual(
                lock, job, task, environment_digest, api_key, base_url,
                max_output_tokens, residual_rounds,
            )
        else:
            raise ContractError("AX-ARENA scheduled unknown condition")
        _append_jsonl(output / "traces.jsonl", trace.payload())
        traces.append(trace)

    return traces
