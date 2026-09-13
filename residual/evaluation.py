"""Matched controller ablations; live models require an explicit config."""
from __future__ import annotations

import statistics

from .config import build_harness
from .demo import DemoProvider, make_case


def benchmark(config, cases=8, noise_lines=256, modes=None, repeats=1, tasks=None):
    modes = modes or ["local_only", "full_cloud", "cascade", "residual_fixed", "residual", "no_pull"]
    workload = tasks if tasks is not None else [make_case(i, noise_lines) for i in range(cases)]
    if not workload:
        raise ValueError("benchmark requires at least one task")
    results = []
    for repeat in range(repeats):
        for index, task in enumerate(workload):
            # Rotate evaluation order to reduce fixed ordering effects in live runs.
            ordered = modes[index % len(modes):] + modes[:index % len(modes)]
            for mode in ordered:
                harness = build_harness(config, mode=mode, disable_cache=True)
                result = harness.run(task)
                result["repeat"] = repeat
                results.append(result)
    probe = build_harness(config, disable_cache=True)
    simulated = any(isinstance(p, DemoProvider) for p in (probe.local, probe.expert) if p)
    summary = []
    for mode in modes:
        rows = [r for r in results if r["mode"] == mode]
        success = sum(r["success"] for r in rows)
        total_bytes = sum(r["metrics"]["remote_request_bytes"] for r in rows)
        usage_complete = all(r["metrics"]["remote_usage_complete"] for r in rows)
        cost_complete = all(r["metrics"]["remote_cost_usd"] is not None for r in rows)
        cost = sum(r["metrics"]["remote_cost_usd"] for r in rows) if cost_complete else None
        summary.append({"mode": mode, "runs": len(rows), "successful": success,
                        "success_rate": success / len(rows),
                        "remote_request_bytes": total_bytes,
                        "remote_bytes_per_success": total_bytes / success if success else None,
                        "remote_calls": sum(r["metrics"]["remote_calls"] for r in rows),
                        "input_tokens_reported": sum(r["metrics"]["remote_input_tokens_reported"] for r in rows),
                        "output_tokens_reported": sum(r["metrics"]["remote_output_tokens_reported"] for r in rows),
                        "usage_complete": usage_complete, "remote_cost_usd": cost,
                        "remote_cost_per_success_usd": cost / success if cost is not None and success else None,
                        "median_elapsed_ms": statistics.median(r["metrics"]["elapsed_ms"] for r in rows)})
    return {"schema_version": "residual.benchmark.v1", "simulation": simulated,
            "workload": "custom_task_suite" if tasks is not None else "synthetic_incident_v1",
            "cases": len(workload), "noise_lines": None if tasks is not None else noise_lines, "repeats": repeats,
            "limitations": ["Synthetic workloads; task success means declared checks passed.",
                            "Scripted providers measure controller behavior, not LLM accuracy or real token savings.",
                            "Request bytes include protocol framing; provider-reported tokens are recorded separately.",
                            "Local hardware/energy and engineering costs are not measured.",
                            "All modes share checks and limits; caches are disabled; no hidden gold is sent to models."],
            "summary": summary, "runs": results}


def markdown_report(report):
    lines = ["# RESIDUAL controller evaluation", "",
             "Scripted simulation. No live LLM performance or billing claim." if report["simulation"]
             else "Live provider evaluation on synthetic incident workloads.", "",
             "| Mode | Passed | Remote calls | Remote request bytes | Reported input tokens | Usage complete |",
             "| --- | ---: | ---: | ---: | ---: | --- |"]
    for r in report["summary"]:
        lines.append(f"| {r['mode']} | {r['successful']}/{r['runs']} | {r['remote_calls']} | "
                     f"{r['remote_request_bytes']:,} | {r['input_tokens_reported']:,} | {r['usage_complete']} |")
    lines += ["", *["- " + x for x in report["limitations"]], ""]
    return "\n".join(lines)
