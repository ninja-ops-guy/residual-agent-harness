#!/usr/bin/env python3
"""bench_mutation.py -- mutation testing for benchmark verifiers.

Applies small perturbations (mutations) to benchmark items and confirms the
verifier under test FAILS each mutated item. A mutation that still passes
"survives" and indicates a verifier blind spot.

This tool is GENERIC over a verifier interface. It does not author, modify,
or select benchmark items or content; it only perturbs existing items to
test verifier robustness.

Verifier interface: a Python callable
    verify(item: dict) -> bool          # True = item passes verification
loaded from a file via --verifier path/to/verifier.py::function_name.

No network calls. Stdlib only.
"""

import argparse
import copy
import hashlib
import importlib.util
import json
import sys


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _flip_digest(value):
    return "sha256:" + hashlib.sha256(("mutated:" + str(value)).encode()).hexdigest()


def mutate_expected_output(item):
    m = copy.deepcopy(item)
    exp = m.get("expected_output")
    if isinstance(exp, dict):
        exp["_mutation"] = "perturbed"
        for k in exp:
            if k != "_mutation":
                exp[k] = ("MUTATED" if isinstance(exp[k], str)
                          else None if exp[k] is None else exp[k])
                break
    elif isinstance(exp, str):
        m["expected_output"] = exp + "_MUTATED"
    elif isinstance(exp, list):
        m["expected_output"] = list(reversed(exp)) or ["MUTATED"]
    else:
        m["expected_output"] = {"_mutation": "perturbed"}
    return m


def mutate_authority(item):
    m = copy.deepcopy(item)
    state = m.setdefault("input_state", {})
    auth = state.setdefault("authority", {})
    granted = list(auth.get("granted", []))
    auth["granted"] = [g for g in granted if g != "spend"]
    state["requested_action"] = "spend"  # now outside granted authority
    return m


def mutate_budget(item):
    m = copy.deepcopy(item)
    state = m.setdefault("input_state", {})
    for key in ("budget_remaining_usd", "budget_usd", "budget"):
        if key in state and isinstance(state[key], (int, float)):
            state[key] = 0 if state[key] > 0 else state[key] + 10_000
            return m
    state["budget_remaining_usd"] = 0
    return m


def mutate_hash(item):
    m = copy.deepcopy(item)
    if "content_digest" in m:
        m["content_digest"] = _flip_digest(m["content_digest"])
    else:
        m["content_digest"] = _flip_digest(canonical(m))
    return m


def mutate_evidence_refs(item):
    m = copy.deepcopy(item)
    state = m.setdefault("input_state", {})
    refs = state.get("evidence_refs")
    if isinstance(refs, list) and refs:
        refs[0] = _flip_digest(refs[0])
    else:
        state["evidence_refs"] = [_flip_digest("missing-evidence")]
    return m


MUTATORS = {
    "expected_output": mutate_expected_output,
    "authority": mutate_authority,
    "budget": mutate_budget,
    "hash": mutate_hash,
    "evidence_refs": mutate_evidence_refs,
}


def load_verifier(spec):
    """Load 'path/to/file.py::function_name' as the verifier callable."""
    if "::" not in spec:
        raise ValueError("--verifier must be 'path/to/file.py::function'")
    path, func_name = spec.split("::", 1)
    module_name = "bench_mutation_verifier_" + hashlib.sha1(
        path.encode()).hexdigest()[:8]
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError("cannot load verifier module from %s" % path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    fn = getattr(module, func_name, None)
    if not callable(fn):
        raise ValueError("%s is not callable in %s" % (func_name, path))
    return fn


def run(items, verifier, mutator_names):
    per_verifier = {}
    detail = []
    for name in mutator_names:
        mutator = MUTATORS[name]
        total = survived = errors = 0
        for item in items:
            iid = item.get("item_id", "?")
            mutated = mutator(item)
            total += 1
            try:
                passed = bool(verifier(mutated))
            except Exception as exc:  # verifier crash = correct rejection
                passed = False
                detail.append({"item_id": iid, "mutation": name,
                               "result": "verifier_error", "error": str(exc)})
                errors += 1
            if passed:
                survived += 1
                detail.append({"item_id": iid, "mutation": name,
                               "result": "SURVIVED"})
        rate = (survived / total) if total else 0.0
        per_verifier[name] = {"mutants": total, "survived": survived,
                              "verifier_errors": errors,
                              "survival_rate": round(rate, 6)}
    return per_verifier, detail


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Mutation-test benchmark verifiers. Each mutation must "
                    "make the verifier FAIL; surviving mutants indicate "
                    "verifier blind spots. Does not author benchmark items.")
    ap.add_argument("benchmark", help="JSONL of benchmark items")
    ap.add_argument("--verifier", required=True,
                    help="verifier spec 'path/to/file.py::function_name'")
    ap.add_argument("--mutations", default=",".join(MUTATORS),
                    help="comma-separated subset of: " + ",".join(MUTATORS))
    ap.add_argument("--report", default="-",
                    help="write JSON report here, or '-' for stdout")
    args = ap.parse_args(argv)

    names = [n.strip() for n in args.mutations.split(",") if n.strip()]
    unknown = [n for n in names if n not in MUTATORS]
    if unknown:
        print("unknown mutations: %s" % unknown, file=sys.stderr)
        return 2

    try:
        verifier = load_verifier(args.verifier)
    except (ValueError, OSError) as exc:
        print("verifier load failed: %s" % exc, file=sys.stderr)
        return 2

    items = []
    with open(args.benchmark, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print("line %d: invalid JSON: %s" % (lineno, exc), file=sys.stderr)
                return 2
    if not items:
        print("benchmark contains no items", file=sys.stderr)
        return 2

    per_verifier, detail = run(items, verifier, names)
    report = {"benchmark": args.benchmark, "verifier": args.verifier,
              "items": len(items), "per_mutation": per_verifier,
              "survived_detail": [d for d in detail
                                  if d["result"] == "SURVIVED"]}
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report == "-":
        sys.stdout.write(text)
    else:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text)
    total_survived = sum(v["survived"] for v in per_verifier.values())
    if total_survived:
        print("WARNING: %d mutants survived" % total_survived, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
