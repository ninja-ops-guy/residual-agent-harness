"""Run with `python -m residual` or the installed `residual` entry point."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import build_harness, load_config
from .core import ContractError, Task, digest, positive_int, strict_json
from .demo import make_case
from .engine import MODES
from .evaluation import benchmark, markdown_report
from .storage import verify_ledger


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "doctor":
        from .factory.doctor import main as doctor
        return doctor(argv[1:])
    if argv and argv[0] == "evaluate":
        from .factory.eval_framework import run_cli as evaluate
        return evaluate(argv[1:])
    if argv and argv[0] == "factory":
        from .factory.cli import main as factory
        return factory(argv[1:])
    if argv and argv[0] == "study":
        from .study import main as study
        return study(argv[1:])
    if argv and argv[0] == "serve":
        from .station.server import main as serve
        return serve(argv[1:])
    if argv and argv[0] == "worker":
        from .station.worker import main as worker
        return worker(argv[1:])
    parser = argparse.ArgumentParser(description="RESIDUAL — hybrid agents with verifiable task boundaries")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Validate Factory host, Ollama and concurrency prerequisites")
    sub.add_parser("factory", help="Plan and approve headless multi-swarm Factory Mode work")
    sub.add_parser("evaluate", help="Run a frozen Factory evaluation (evaluate --help for options)")
    sub.add_parser("serve", help="Open the local web command station (serve --help for options)")
    sub.add_parser("worker", help="Connect a distributed inference runner")
    sub.add_parser("study", help="Freeze/run independently graded studies (study --help)")
    for name in ("demo", "run"):
        run = sub.add_parser(name)
        if name == "run":
            run.add_argument("task")
            run.add_argument("--config", required=True, help="TOML providers and limits; no implicit demo fallback")
        else:
            run.add_argument("--config", help="Omit for clearly labelled scripted demonstration")
        run.add_argument("--mode", choices=sorted(MODES), default="residual")
        run.add_argument("--output", default="runs/latest")
        run.add_argument("--no-cache", action="store_true")
    bench = sub.add_parser("benchmark")
    bench.add_argument("--config", help="Explicit config enables real provider calls; each mode incurs its own usage")
    bench.add_argument("--cases", type=int, default=8)
    bench.add_argument("--noise-lines", type=int, default=256)
    bench.add_argument("--repeats", type=int, default=1)
    bench.add_argument("--modes", nargs="+", choices=sorted(MODES))
    bench.add_argument("--task-suite", help="JSON array of task paths relative to this suite file; replaces synthetic cases")
    bench.add_argument("--output", default="runs/benchmark.json")
    verify = sub.add_parser("verify-trace")
    verify.add_argument("trace")
    verify.add_argument("--expected-root")
    verify.add_argument("--result", help="Also check the final event binds this result JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-trace":
            result = verify_ledger(args.trace, args.expected_root)
            if args.result:
                value = strict_json(Path(args.result).read_text())
                root = value.pop("trace_root")
                terminal = strict_json(Path(args.trace).read_text().splitlines()[-1])
                if root != result["root"] or digest(value) != terminal["data"]["result_sha256"]:
                    raise ContractError("result does not match trace commitment")
                result["result_bound"] = True
            print(json.dumps(result, indent=2))
            return 0
        config = load_config(args.config)
        if args.command == "benchmark":
            for name in ("cases", "noise_lines", "repeats"):
                positive_int(getattr(args, name), name)
            tasks = None
            if args.task_suite:
                suite = Path(args.task_suite).resolve()
                entries = strict_json(suite.read_text())
                if not isinstance(entries, list) or not entries or any(not isinstance(e, str) for e in entries):
                    raise ContractError("task suite must be a nonempty array of paths")
                paths = [(suite.parent / entry).resolve() for entry in entries]
                if any(not p.is_relative_to(suite.parent) for p in paths):
                    raise ContractError("task suite path escapes suite directory")
                tasks = [Task.load(p) for p in paths]
            report = benchmark(config, args.cases, args.noise_lines, args.modes, args.repeats, tasks)
            write_json(args.output, report)
            Path(args.output).with_suffix(".md").write_text(markdown_report(report))
            print(markdown_report(report))
            return 0
        task = Task.load(args.task) if args.command == "run" else make_case()
        harness = build_harness(config, args.mode, args.no_cache)
        try:
            result = harness.run(task)
            destination = Path(args.output)
            write_json(destination / "result.json", result)
            harness.ledger.write(destination / "trace.jsonl")
        finally:
            if harness.cache:
                harness.cache.close()
        print(json.dumps({"task_id": result["task_id"], "status": result["status"],
                          "values": result["values"], "unresolved": result["unresolved"],
                          "metrics": result["metrics"], "output": str(destination),
                          "simulation": any(c["usage"]["source"] == "simulation" for c in result["calls"])}, indent=2))
        return 0 if result["success"] else 2
    except (ContractError, OSError, ValueError, TypeError, KeyError, ImportError, AttributeError) as exc:
        print(f"residual: {type(exc).__name__}: configuration, task, or trace could not be validated", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
