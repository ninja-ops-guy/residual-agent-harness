"""Evaluation runner CLI for EXP-M6-SLM (SLM-01..05).

Executes a frozen Control Bench v0 benchmark JSONL through the category
verifier suite and aggregates the frozen metrics of EVALUATION-PROTOCOL.md,
emitting a results-store-format run record (research/slm/eval/results_store.py).

Guarantees (hard rules):
* items are NEVER mutated (passed to backends/verifiers as read-only views);
* every item's ``digest`` is verified (sha256 over the canonical JSON of the
  item minus its digest field) BEFORE any backend runs on it; a mismatch is a
  BENCHMARK_DEFECT and the backend is never invoked for that item;
* unknown verifier_ref -> BENCHMARK_DEFECT propagation (never scored as
  success, never silently repaired);
* safety metrics (fner, avr) are computed and reported separately and are
  NEVER aggregated into vmsr;
* the runner never trains, never tunes, and never inspects results to modify
  the benchmark.

CLI:
  python -m research.slm.eval.runner.runner \
      --benchmark bench.jsonl --backend b3-oracle \
      --condition A --seed-index 0 \
      --model-hash <sha256> --benchmark-hash <sha256> \
      --hardware "cpu-only" --out record.json [--store runs.jsonl]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .backends import BACKENDS, ModelBackend, MalformedOutput
from . import stats as stats_mod

SCHEMA_VERSION = "slm-eval-runner-v0"

# Frozen metric names emitted into the results-store `metrics` object. Only
# names in results_store.KNOWN_METRICS may appear there; per-category
# breakdowns live under the non-metric "per_category" field instead.
FROZEN_METRIC_FIELDS = (
    "vmsr", "fner", "avr", "uer", "schema_invalid_rate",
    "latency_ms_median", "latency_ms_p95", "latency_ms_p99",
)


def canonical_json(obj: Any) -> bytes:
    """Deterministic serialization (matches results_store.canonical_json)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def item_digest(item: Mapping[str, Any]) -> str:
    """SHA-256 over the item with its own ``digest`` field excluded."""
    body = {k: v for k, v in item.items() if k != "digest"}
    return hashlib.sha256(canonical_json(body)).hexdigest()


def _normalize_digest(value: Any) -> str:
    if isinstance(value, str) and value.startswith("sha256:"):
        return value[len("sha256:"):]
    return value if isinstance(value, str) else ""


def load_benchmark(path: str) -> List[Dict[str, Any]]:
    """Load a Control Bench v0 JSONL file. Items are returned verbatim."""
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("%s:%d: corrupt benchmark line: %s"
                                 % (path, lineno, exc))
            if not isinstance(item, dict):
                raise ValueError("%s:%d: benchmark item is not an object" % (path, lineno))
            items.append(item)
    return items


def default_dispatch(item: Mapping[str, Any], candidate: Any):
    """Dispatch via the Lane D verifier suite; unknown refs -> DEFECT."""
    from research.slm import verifiers  # lazy: suite on slm00/verifiers
    return verifiers.verify(dict(item), candidate)


def _null_verifier_result(verdict: str, reason_code: str, detail: str = ""):
    try:
        from research.slm.verifiers.base import Verdict, VerifierResult
        return VerifierResult(Verdict(verdict), reason_code, detail)
    except Exception:
        return {"verdict": verdict, "reason_code": reason_code,
                "detail": detail}


def _verdict_of(result: Any) -> str:
    verdict = getattr(result, "verdict", None)
    if verdict is not None:
        return getattr(verdict, "value", str(verdict))
    if isinstance(result, Mapping):
        return str(result.get("verdict"))
    return str(result)


def _reason_of(result: Any) -> str:
    reason = getattr(result, "reason_code", None)
    if reason is not None:
        return str(reason)
    if isinstance(result, Mapping):
        return str(result.get("reason_code", ""))
    return ""


def _percentile(values: Sequence[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    if n == 1:
        return ordered[0]
    rank = (q / 100.0) * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def _safety_observables(candidate: Any) -> Dict[str, Any]:
    """Extract observation-shaped safety fields from a candidate, if present.

    fner/avr are computed ONLY from explicitly declared observation fields
    (``escalation.required``/``escalation.classification``,
    ``authority.violation``). Absent fields mean "not measurable" for that
    item -- never imputed (protocol section 8).
    """
    out: Dict[str, Any] = {}
    if not isinstance(candidate, Mapping):
        return out
    esc = candidate.get("escalation")
    if isinstance(esc, Mapping):
        if esc.get("required") is True:
            out["escalation_required"] = True
            out["false_non_escalation"] = (
                esc.get("classification") == "false_non_escalation")
        if esc.get("taken") is True:
            out["escalation_taken"] = True
            out["unnecessary_escalation"] = (
                esc.get("classification") == "unnecessary_escalation")
    auth = candidate.get("authority")
    if isinstance(auth, Mapping) and "violation" in auth:
        out["authority_violation"] = bool(auth.get("violation"))
    return out


def run_evaluation(
    items: Sequence[Mapping[str, Any]],
    backend: ModelBackend,
    *,
    seed: int,
    dispatch: Callable[[Mapping[str, Any], Any], Any] = default_dispatch,
) -> Dict[str, Any]:
    """Execute all items and aggregate frozen metrics. Never mutates items."""
    if seed not in stats_mod.FROZEN_SEEDS:
        raise ValueError("seed %r not in frozen seed list %s"
                         % (seed, stats_mod.FROZEN_SEEDS))
    rng = random.Random(seed)
    records: List[Dict[str, Any]] = []
    for item in items:
        readonly = MappingProxyType(dict(item))  # shallow read-only view
        rec: Dict[str, Any] = {
            "item_id": item.get("item_id"),
            "category": item.get("category"),
            "contamination_group": item.get("contamination_group"),
            "safety_critical": bool(item.get("safety_critical", False)),
            "difficulty": item.get("difficulty"),
        }
        # 1. Verify item digest BEFORE any backend invocation.
        declared = _normalize_digest(item.get("digest"))
        if not declared:
            rec.update(verdict="BENCHMARK_DEFECT", reason_code="ITEM_MISSING_DIGEST")
            records.append(rec)
            continue
        if declared != item_digest(item):
            rec.update(verdict="BENCHMARK_DEFECT", reason_code="DIGEST_MISMATCH")
            records.append(rec)
            continue
        # 2. Backend invocation (timed; latency is a frozen secondary metric).
        start = time.perf_counter()
        candidate = backend.predict(readonly, rng)
        rec["latency_ms"] = (time.perf_counter() - start) * 1000.0
        rec["schema_invalid"] = not isinstance(candidate, Mapping) or isinstance(
            candidate, MalformedOutput)
        # 3. Verifier dispatch; unknown verifier_ref -> BENCHMARK_DEFECT.
        result = dispatch(readonly, candidate)
        rec["verdict"] = _verdict_of(result)
        rec["reason_code"] = _reason_of(result)
        # 4. Safety observables -- separate stream, never folded into vmsr.
        rec.update({k: v for k, v in _safety_observables(candidate).items()})
        records.append(rec)
    return {"records": records, "metrics": _aggregate(records)}


def _rate(numer: int, denom: int) -> Optional[float]:
    return (numer / denom) if denom else None


def _aggregate(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate frozen metrics per category and in aggregate.

    BENCHMARK_DEFECT items are EXCLUDED from all metric denominators (they are
    benchmark defects, not configuration outcomes; protocol section 8(b)) and
    reported as their own count. FAIL and schema-invalid outputs count as
    failures attributed to the configuration.
    """
    def block(recs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        scored = [r for r in recs if r.get("verdict") in ("PASS", "FAIL")]
        defects = [r for r in recs if r.get("verdict") == "BENCHMARK_DEFECT"]
        passed = [r for r in scored if r["verdict"] == "PASS"]
        invalid = [r for r in scored if r.get("schema_invalid")]
        lat = [float(r["latency_ms"]) for r in scored if "latency_ms" in r]
        # Safety metrics: strictly separate, never aggregated into vmsr.
        esc_req = [r for r in scored if r.get("escalation_required")]
        fne = [r for r in esc_req if r.get("false_non_escalation")]
        auth = [r for r in scored if "authority_violation" in r]
        av = [r for r in auth if r.get("authority_violation")]
        auth_sc = [r for r in auth if r.get("safety_critical")]
        av_sc = [r for r in auth_sc if r.get("authority_violation")]
        esc_taken = [r for r in scored if r.get("escalation_taken")]
        ue = [r for r in esc_taken if r.get("unnecessary_escalation")]
        return {
            "n_total": len(recs),
            "n_scored": len(scored),
            "n_benchmark_defects": len(defects),
            "defect_reason_codes": sorted({_reason_of(r) or r.get("reason_code", "")
                                           for r in defects}),
            "vmsr": _rate(len(passed), len(scored)),
            "schema_invalid_rate": _rate(len(invalid), len(scored)),
            "fner": _rate(len(fne), len(esc_req)),
            "avr": _rate(len(av), len(auth)),
            "avr_safety_critical": _rate(len(av_sc), len(auth_sc)),
            "uer": _rate(len(ue), len(esc_taken)),
            "latency_ms_median": _percentile(lat, 50),
            "latency_ms_p95": _percentile(lat, 95),
            "latency_ms_p99": _percentile(lat, 99),
        }

    per_category: Dict[str, Any] = {}
    categories = sorted({str(r.get("category")) for r in records})
    for cat in categories:
        per_category[cat] = block([r for r in records
                                   if str(r.get("category")) == cat])
    return {"aggregate": block(records), "per_category": per_category}


def build_store_record(
    result: Mapping[str, Any],
    *,
    model_hash: str,
    benchmark_hash: str,
    harness_condition: str,
    seed: int,
    seed_index: int,
    hardware: str,
    backend_name: str,
) -> Dict[str, Any]:
    """Shape a run result into the results-store record format.

    ``metrics`` carries ONLY frozen metric names (results_store.KNOWN_METRICS);
    per-category breakdowns and defect accounting live outside ``metrics`` so
    the record passes results_store.validate_record unchanged.
    """
    agg = result["metrics"]["aggregate"]
    metrics = {name: agg.get(name) for name in FROZEN_METRIC_FIELDS
               if agg.get(name) is not None}
    return {
        "model_hash": model_hash,
        "benchmark_hash": benchmark_hash,
        "harness_condition": harness_condition,
        "seed": seed,
        "seed_index": seed_index,
        "hardware": hardware,
        "metrics": metrics,
        "backend": backend_name,
        "runner_schema_version": SCHEMA_VERSION,
        "per_category": result["metrics"]["per_category"],
        "n_benchmark_defects": agg["n_benchmark_defects"],
        "safety": {  # strictly separate; never aggregated into vmsr
            "fner": agg.get("fner"),
            "avr": agg.get("avr"),
            "avr_safety_critical": agg.get("avr_safety_critical"),
        },
    }


def append_to_store(store_path: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Append via research/slm/eval/results_store.py (digest-chained)."""
    from research.slm.eval import results_store
    return results_store.append_record(store_path, record)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="SLM-01..05 shared evaluation runner (frozen protocol).")
    parser.add_argument("--benchmark", required=True,
                        help="Control Bench v0 JSONL path")
    parser.add_argument("--backend", required=True, choices=sorted(BACKENDS),
                        help="model backend (B0/B1/B2/B3 floors+oracle or http)")
    parser.add_argument("--backend-arg", default=None,
                        help="backend argument: train-stats JSON path "
                             "(b2-trivial-majority) or endpoint URL (http-external)")
    parser.add_argument("--condition", required=True,
                        choices=list("ABCDEF"), help="harness condition A-F")
    parser.add_argument("--seed-index", type=int, required=True,
                        help="index into the frozen seed list (0-4)")
    parser.add_argument("--model-hash", required=True)
    parser.add_argument("--benchmark-hash", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--out", help="write the store-format record JSON here")
    parser.add_argument("--store", help="append the record to this JSONL store")
    parser.add_argument("--items-out", help="write per-item records JSONL here")
    args = parser.parse_args(argv)

    seed = stats_mod.frozen_seed(args.seed_index)
    backend_cls = BACKENDS[args.backend]
    if args.backend == "b2-trivial-majority":
        if not args.backend_arg:
            parser.error("--backend-arg (train-split stats JSON) required for b2")
        backend = backend_cls(args.backend_arg)
    elif args.backend == "http-external":
        if not args.backend_arg:
            parser.error("--backend-arg (endpoint URL) required for http-external")
        backend = backend_cls(args.backend_arg)
    else:
        backend = backend_cls()

    items = load_benchmark(args.benchmark)
    result = run_evaluation(items, backend, seed=seed)
    record = build_store_record(
        result, model_hash=args.model_hash, benchmark_hash=args.benchmark_hash,
        harness_condition=args.condition, seed=seed, seed_index=args.seed_index,
        hardware=args.hardware, backend_name=args.backend)

    if args.items_out:
        with open(args.items_out, "w", encoding="utf-8") as fh:
            for rec in result["records"]:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, sort_keys=True)
            fh.write("\n")
    if args.store:
        stored = append_to_store(args.store, record)
        print(json.dumps({"run_id": stored["run_id"],
                          "digest": stored["digest"]}, indent=2))
    else:
        print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
