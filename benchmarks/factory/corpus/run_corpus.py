from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from common import BENCHMARKS, CONFIGS, CorpusManifest, host_evidence, report_entry  # noqa: E402
from residual.core import strict_json  # noqa: E402
from residual.factory.evidence_receipts import StationIdentity  # noqa: E402


def _run(argv: list[str], *, cwd: Path = ROOT) -> None:
    proc = subprocess.run(argv, cwd=cwd, check=False)
    if proc.returncode:
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(argv)}")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _require_clean_source() -> str:
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("tracked source tree must be clean before corpus execution")
    return _git("rev-parse", "HEAD")


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _live_model_digest(base_url: str, model: str) -> str:
    with urllib.request.urlopen(base_url.rstrip('/') + '/api/tags', timeout=10) as response:
        payload = json.load(response)
    for item in payload.get('models', []):
        if item.get('name') == model or item.get('model') == model:
            digest = item.get('digest')
            if isinstance(digest, str) and digest:
                return digest
    raise SystemExit(f"model {model!r} is not installed at {base_url}")


def _summary(report: dict) -> dict:
    configs = report.get("configurations") or {}
    out = {}
    for config in CONFIGS:
        row = configs.get(config) or {}
        metrics = row.get("metrics") or {}
        selected = {}
        for name in ("elapsed_time_minutes", "accepted_tasks_per_hour", "token_cost_total",
                     "gpu_time_minutes", "coordination_overhead_pct", "rework_rate_pct",
                     "merge_conflicts", "verifier_rejection_rate_pct", "final_test_pass_rate_pct",
                     "total_cost_usd", "cost_per_accepted_task_usd"):
            stat = metrics.get(name)
            if isinstance(stat, dict):
                selected[name] = {k: stat.get(k) for k in ("mean", "median", "stddev")}
        out[config] = {
            "speedup_vs_single": row.get("speedup_vs_single"),
            "parallel_efficiency": row.get("parallel_efficiency"),
            "observed_peak_workers": row.get("observed_peak_workers"),
            "simulation": row.get("simulation"),
            "metrics": selected,
        }
    return out


def _load_or_create_identity(output: Path, resume: bool) -> tuple[StationIdentity, Path, bytes]:
    key_path = output / "station.pem"
    public_path = output / "station-public-key.hex"
    if resume:
        if not key_path.exists():
            raise SystemExit("resume requires the original station.pem; a completed corpus cannot be resumed")
        identity = StationIdentity.load_private(key_path)
    else:
        identity = StationIdentity.generate()
        identity.save_private(key_path)
    public_key = identity.public_bytes()
    if public_path.exists():
        if public_path.read_text(encoding="ascii").strip() != public_key.hex():
            raise SystemExit("station public key does not match resume private key")
    else:
        public_path.write_text(public_key.hex() + "\n", encoding="ascii")
    return identity, key_path, public_key


def _resume_identity(output: Path, source_commit: str, host: dict, runs: int) -> dict:
    source_path = output / "source-commit.txt"
    host_path = output / "host.json"
    state_path = output / "corpus-state.json"
    if source_path.read_text(encoding="utf-8").strip() != source_commit:
        raise SystemExit("resume refused: source commit changed")
    old_host = strict_json(host_path.read_text(encoding="utf-8"))
    if old_host.get("fingerprint") != host.get("fingerprint"):
        raise SystemExit("resume refused: host fingerprint changed")
    state = strict_json(state_path.read_text(encoding="utf-8"))
    if state.get("source_commit") != source_commit or state.get("host_fingerprint") != host.get("fingerprint"):
        raise SystemExit("resume refused: corpus state identity mismatch")
    if state.get("runs") != runs or tuple(state.get("configs", ())) != CONFIGS:
        raise SystemExit("resume refused: run count/configuration changed")
    return state


def main() -> int:
    p = argparse.ArgumentParser(description="Run the measured FB001-FB004 Factory benchmark corpus on one host/model")
    p.add_argument("--model", required=True, help="Installed Ollama model, e.g. qwen2.5-coder:7b")
    p.add_argument("--base-url", default="http://localhost:11434")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--output", default="runs/factory-corpus")
    p.add_argument("--dry-run", action="store_true", help="prepare and verify all workloads without model benchmark calls")
    p.add_argument("--resume", action="store_true", help="reuse completed benchmark reports only when source/host/model identity matches")
    args = p.parse_args()
    if args.runs < 3:
        raise SystemExit("corpus requires at least 3 runs per configuration")
    if args.dry_run and args.resume:
        raise SystemExit("--dry-run and --resume are mutually exclusive")

    output = Path(args.output).resolve()
    if args.resume:
        if not output.exists():
            raise SystemExit("resume output directory does not exist")
    elif output.exists() and any(output.iterdir()):
        raise SystemExit("corpus output directory must be absent or empty")
    output.mkdir(parents=True, exist_ok=True)

    source_commit = _require_clean_source()
    host = host_evidence()
    live_digest = _live_model_digest(args.base_url, args.model)
    if args.resume:
        state = _resume_identity(output, source_commit, host, args.runs)
        if state.get("model_request") != args.model:
            raise SystemExit("resume refused: model request changed")
        if state.get("model_version") and state.get("model_version") != live_digest:
            raise SystemExit("resume refused: live Ollama model digest changed")
    else:
        _write_json(output / "host.json", host)
        (output / "source-commit.txt").write_text(source_commit + "\n", encoding="utf-8")
        state = {
            "schema_version": "factory-benchmark-corpus-state-v1",
            "source_commit": source_commit,
            "host_fingerprint": host["fingerprint"],
            "runs": args.runs,
            "configs": list(CONFIGS),
            "model_request": args.model,
            "model_version": live_digest,
            "completed": [],
        }
        _write_json(output / "corpus-state.json", state)

    identity, key_path, public_key = _load_or_create_identity(output, args.resume)
    state_path = output / "corpus-state.json"
    completed = list(state.get("completed", []))

    entries = []
    model_name = None
    model_version = None
    summaries = {}
    dry_workloads = []

    for benchmark in BENCHMARKS:
        if host_evidence()["fingerprint"] != host["fingerprint"]:
            raise SystemExit(f"host fingerprint changed before {benchmark}")
        if _git("rev-parse", "HEAD") != source_commit or _git("status", "--porcelain", "--untracked-files=no"):
            raise SystemExit(f"source revision changed before {benchmark}")
        if _live_model_digest(args.base_url, args.model) != live_digest:
            raise SystemExit(f"live Ollama model digest changed before {benchmark}")

        bench_dir = ROOT / "benchmarks" / "factory" / benchmark
        bench_out = output / benchmark
        workload_path = bench_out / "workload.json"
        results_dir = bench_out / "results"
        report_path = results_dir / "comparison-report.json"
        bench_out.mkdir(parents=True, exist_ok=True)

        if not workload_path.exists():
            _run([sys.executable, str(bench_dir / "prepare_workload.py"),
                  "--model", args.model, "--base-url", args.base_url,
                  "--output", str(workload_path), "--station-key", str(key_path)])
        workload_raw = strict_json(workload_path.read_text(encoding="utf-8"))
        engine = workload_raw.get("engine") or {}
        current_name, current_version = str(engine.get("name", "")), str(engine.get("version", ""))
        if not current_name or not current_version:
            raise SystemExit(f"{benchmark} workload lacks frozen engine identity")
        if current_version != live_digest:
            raise SystemExit(f"{benchmark} frozen workload digest does not match live Ollama model")
        if model_name is None:
            model_name, model_version = current_name, current_version
        elif (current_name, current_version) != (model_name, model_version):
            raise SystemExit(f"model identity drift detected at {benchmark}")

        if args.dry_run:
            dry_workloads.append({"benchmark": benchmark, "workload": str(workload_path),
                                  "engine_name": current_name, "engine_version": current_version})
            continue

        if args.resume and benchmark in completed:
            if not report_path.exists():
                raise SystemExit(f"resume state marks {benchmark} complete but report is missing")
        else:
            _run([sys.executable, "-m", "residual", "evaluate",
                  "--workload", str(workload_path), "--configs", ",".join(CONFIGS),
                  "--runs", str(args.runs), "--station-key", str(key_path),
                  "--output", str(results_dir)])
        if _live_model_digest(args.base_url, args.model) != live_digest:
            raise SystemExit(f"live Ollama model digest changed during {benchmark}")
        entry = report_entry(benchmark, workload_path, report_path, public_key)
        if entry.simulation:
            raise SystemExit(f"{benchmark} produced simulated evidence; corpus will not be signed as measured")
        entries.append(entry)
        summaries[benchmark] = _summary(strict_json(report_path.read_text(encoding="utf-8")))
        if benchmark not in completed:
            completed.append(benchmark)
            state["completed"] = completed
            state["model_name"] = model_name
            state["model_version"] = model_version
            _write_json(state_path, state)

    if args.dry_run:
        _write_json(output / "dry-run.json", {
            "schema_version": "factory-benchmark-corpus-dry-run-v1",
            "status": "ready",
            "source_commit": source_commit,
            "host_fingerprint": host["fingerprint"],
            "model_name": model_name,
            "model_version": model_version,
            "runs": args.runs,
            "configs": list(CONFIGS),
            "benchmark_executions": len(BENCHMARKS) * len(CONFIGS) * args.runs,
            "workloads": dry_workloads,
        })
        key_path.unlink(missing_ok=True)
        print(json.dumps({"status": "dry_run_ready", "benchmarks": list(BENCHMARKS),
                          "benchmark_executions": len(BENCHMARKS) * len(CONFIGS) * args.runs,
                          "output": str(output)}, indent=2))
        return 0

    if host_evidence()["fingerprint"] != host["fingerprint"]:
        raise SystemExit("host fingerprint changed during corpus execution")
    if _git("rev-parse", "HEAD") != source_commit or _git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("source revision changed during corpus execution")
    if _live_model_digest(args.base_url, args.model) != live_digest:
        raise SystemExit("live Ollama model digest changed during corpus execution")

    manifest = CorpusManifest.issue(source_commit=source_commit, model_name=model_name,
                                    model_version=model_version, host=host, runs=args.runs,
                                    entries=tuple(entries), identity=identity)
    if manifest.simulation:
        raise SystemExit("measured corpus unexpectedly contains simulated child report")
    _write_json(output / "corpus-manifest.json", manifest.to_dict())
    _write_json(output / "corpus-summary.json", {
        "schema_version": "factory-benchmark-corpus-summary-v1",
        "manifest_hash": manifest.manifest_hash,
        "source_commit": source_commit,
        "model_name": model_name,
        "model_version": model_version,
        "host_fingerprint": host["fingerprint"],
        "runs": args.runs,
        "configs": list(CONFIGS),
        "benchmarks": summaries,
    })
    state["status"] = "complete"
    state["manifest_hash"] = manifest.manifest_hash
    _write_json(state_path, state)
    key_path.unlink(missing_ok=True)
    print(json.dumps({"status": "complete", "manifest_hash": manifest.manifest_hash,
                      "simulation": manifest.simulation, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
