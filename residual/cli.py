"""Run with `python -m residual` or the installed `residual` entry point."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import build_harness, load_config
from .core import ContractError, Task, canonical, digest, positive_int, strict_json
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
    if argv and argv[0] == "factory":
        from .factory.cli import main as factory
        return factory(argv[1:])
    if argv and argv[0] == "evaluate":
        from .eval.cli import main as evaluate
        return evaluate(argv[1:])
    if argv and argv[0] == "study":
        from .study import main as study
        return study(argv[1:])
    if argv and argv[0] == "serve":
        from .station.server import main as serve
        return serve(argv[1:])
    if argv and argv[0] == "worker":
        from .station.worker import main as worker
        return worker(argv[1:])
    if argv and argv[0] == "node":
        from .cluster.cli import node_main
        return node_main(argv[1:])
    if argv and argv[0] == "cluster":
        from .cluster.cli import cluster_main
        return cluster_main(argv[1:])

    parser = argparse.ArgumentParser(description="RESIDUAL — hybrid agents with verifiable task boundaries")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("factory", help="Plan and approve headless multi-swarm Factory Mode work")
    sub.add_parser("evaluate", help="Run SPEC-EVAL-001 comparative evidence (evaluate --help)")
    sub.add_parser("serve", help="Open the local web command station (serve --help for options)")
    sub.add_parser("worker", help="Connect a distributed inference runner")
    sub.add_parser("study", help="Freeze/run independently graded studies (study --help)")
    sub.add_parser("node", help="Join/leave the distributed cluster (node --help)")
    sub.add_parser("cluster", help="Show cluster status (cluster --help)")

    setup_parser = sub.add_parser("setup", help="Guided first-run setup with managed FreeLLMAPI")
    setup_parser.add_argument("--home", help="Residual managed home (default: ~/.residual or RESIDUAL_HOME)")
    setup_parser.add_argument("--provider", choices=("groq", "google", "cerebras", "mistral", "openrouter"))
    setup_parser.add_argument("--provider-key-env", help="Read the upstream provider key from this environment variable")
    setup_parser.add_argument("--unified-key-env", help="Read the FreeLLMAPI unified key from this environment variable")
    setup_parser.add_argument("--model", default="auto", help="FreeLLMAPI model route (default: auto)")
    setup_parser.add_argument("--non-interactive", action="store_true")
    setup_parser.add_argument("--skip-start", action="store_true", help="Write managed files without starting Docker")
    setup_parser.add_argument("--skip-smoke", action="store_true", help="Skip the live Residual worker-contract smoke test")

    doctor_parser = sub.add_parser("doctor", help="Diagnose the local Residual/FreeLLMAPI setup")
    doctor_parser.add_argument("--home", help="Residual managed home (default: ~/.residual or RESIDUAL_HOME)")
    doctor_parser.add_argument("--fix", action="store_true", help="Apply safe deterministic repairs")
    doctor_parser.add_argument("--json", action="store_true", dest="json_output")

    providers_parser = sub.add_parser("providers", help="Show supported FreeLLMAPI upstream provider setup links")
    providers_parser.add_argument("action", nargs="?", choices=("list",), default="list")

    services_parser = sub.add_parser("services", help="Manage Residual-owned local services")
    services_parser.add_argument("action", choices=("install", "start"))
    services_parser.add_argument("service", choices=("freellmapi",))
    services_parser.add_argument("--home", help="Residual managed home (default: ~/.residual or RESIDUAL_HOME)")

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
        if args.command in {"setup", "doctor", "providers", "services"}:
            from .onboarding import (
                ManagedPaths, doctor, ensure_service_files, list_providers,
                print_doctor, setup, start_service,
            )
            if args.command == "providers":
                list_providers()
                return 0
            paths = ManagedPaths.from_value(args.home)
            if args.command == "setup":
                return setup(
                    paths, provider_id=args.provider, provider_key_env=args.provider_key_env,
                    unified_key_env=args.unified_key_env, model=args.model,
                    non_interactive=args.non_interactive, skip_start=args.skip_start,
                    skip_smoke=args.skip_smoke,
                )
            if args.command == "doctor":
                checks = doctor(paths, fix=args.fix)
                if args.json_output:
                    print(json.dumps([c.as_dict() for c in checks], indent=2))
                else:
                    print_doctor(checks)
                return 1 if any(c.status == "fail" for c in checks) else 0
            if args.action == "install":
                changed = ensure_service_files(paths)
                print(json.dumps({"service": args.service, "installed": True, "changed": changed,
                                  "path": str(paths.service_dir)}, indent=2))
                return 0
            ok, detail = start_service(paths)
            print(json.dumps({"service": args.service, "started": ok, "detail": detail}, indent=2))
            return 0 if ok else 1

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
            # Capture identity before cleanup. Summary publication uses the
            # exact persisted result, not a potentially stale memory alias.
            expected_result_hash = digest(result)
            write_json(destination / "result.json", result)
            harness.ledger.write(destination / "trace.jsonl")
        finally:
            if harness.cache:
                harness.cache.close()
        result = strict_json((destination / "result.json").read_text(encoding="utf-8"))
        if digest(result) != expected_result_hash:
            raise ContractError("persisted result changed before summary publication")
        # Use the same strict encoder as evidence hashing. Compact output keeps
        # numeric serialization on that path; no values are clamped or replaced.
        print(canonical({"task_id": result["task_id"], "status": result["status"],
                         "values": result["values"], "unresolved": result["unresolved"],
                         "metrics": result["metrics"], "output": str(destination),
                         "simulation": any(c["usage"]["source"] == "simulation" for c in result["calls"])}))
        return 0 if result["success"] else 2
    except (ContractError, OSError, ValueError, TypeError, KeyError, ImportError, AttributeError) as exc:
        # Config exceptions can contain URLs/keys from custom plugins; default CLI avoids echoing them.
        print(f"residual: {type(exc).__name__}: configuration, task, or trace could not be validated", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
