#!/usr/bin/env python3
"""CLI for the INJ Class C battery v0.2.0 — harness-faithful mode.

Runs vector corpora against the pinned v1 prompt bytes (imported live from
the repo) under the undelimited user-role evidence assembly, classifies
trials into the three-state outcome (COMPLIANCE / NONCOMPLIANCE_NOT_OBSERVED
/ UNEVALUABLE), writes trials.jsonl for the run, and emits one validated
receipt per (vector, variant).

Backends:
  stub  — deterministic scripted providers, offline. claim_scope is ALWAYS
          "harness-verification" (harness mechanics only, never a cognitive
          claim). --stub-mode mixed|benign (default mixed).
  http  — OpenAI-compatible /chat/completions via stdlib urllib, messages =
          [{system: EXACT imported prompt bytes}, {user: assembled evidence}].
          claim_scope "residual-v1-cognitive-measurement". Requires
          --model-identity (operator-declared identity, bound separately from
          the provider's returned model label).

Phases (§4.2): screening requires N>=25, qualification requires N>=100.

Examples:
  python run_harness.py --backend stub --n 25 --phase screening --out ./out
  python run_harness.py --backend stub --stub-mode benign --n 25 --case INJ-V02 --out ./out
  python run_harness.py --backend http --model llama3.1 --base-url http://localhost:11434/v1 \\
      --model-identity "ollama:llama3.1 (operator-declared)" --n 100 --phase qualification --out ./out
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from inj_harness import positions, providers, repo_import, runner, vectors  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="INJ Class C battery v0.2.0 — harness-faithful mode")
    p.add_argument("--repo", default=None,
                   help="v1 repo checkout (default: RESIDUAL_REPO env or ~/workspace/residual-agent-harness)")
    p.add_argument("--backend", choices=["stub", "http"], default="stub")
    p.add_argument("--stub-mode", choices=["mixed", "benign"], default="mixed",
                   help="stub provider mode (stub backend only)")
    p.add_argument("--base-url", default="http://localhost:11434/v1",
                   help="OpenAI-compatible base URL (http backend only)")
    p.add_argument("--model", default=None,
                   help="model name for the HTTP request body (http backend only)")
    p.add_argument("--model-identity", default=None,
                   help="REQUIRED for http: operator-declared exact model identity, "
                        "bound separately from the provider's returned label")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=1.0, dest="top_p")
    p.add_argument("--seed", default="42",
                   help="'none' for provider-default, else an integer seed")
    p.add_argument("--n", type=int, default=25, help="trials per cell")
    p.add_argument("--phase", choices=["screening", "qualification"], default="screening")
    p.add_argument("--out", default=os.path.join(HERE, "out"))
    p.add_argument("--case", action="append", default=None,
                   help="vector id to run (repeatable; default: all 11)")
    p.add_argument("--positions", nargs="*", default=None,
                   help="subset of positions (default: all four)")
    p.add_argument("--max-output-tokens", type=int, default=512)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # 1. Live prompt-byte import — abort on failure (never run against copied bytes).
    try:
        prov = repo_import.import_prompt_bytes(args.repo)
    except repo_import.RepoImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    prompts = {"RUNNER_SYSTEM": prov["runner_system"],
               "REVIEW_SYSTEM": prov["review_system"]}
    if not prov["commit_matches_expected"]:
        print(f"WARNING: repo commit {prov['source_commit'][:12] if prov['source_commit'] != 'unknown (git unavailable)' else prov['source_commit']} "
              f"differs from the build-verified commit {repo_import.EXPECTED_COMMIT_SHORT}...; "
              f"proceeding — the prompt-bytes sha256 in receipts is authoritative.",
              file=sys.stderr)

    # 2. §4.2 N threshold enforcement.
    try:
        runner.check_n_for_phase(args.n, args.phase)
    except runner.NThresholdError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    # 3. Positions and vectors.
    pos_list = list(args.positions) if args.positions else list(positions.POSITIONS)
    unknown = [p for p in pos_list if p not in positions.POSITIONS]
    if unknown:
        print(f"ERROR: unknown positions: {unknown} (valid: {list(positions.POSITIONS)})",
              file=sys.stderr)
        return 2
    case_ids = args.case if args.case else sorted(vectors.VECTORS)
    unknown_cases = [c for c in case_ids if c not in vectors.VECTORS]
    if unknown_cases:
        print(f"ERROR: unknown vector ids: {unknown_cases} (valid: {sorted(vectors.VECTORS)})",
              file=sys.stderr)
        return 2

    # 4. Backend.
    if args.backend == "stub":
        make = providers.stub_provider_factory()
        provider = make(args.stub_mode)
        model_identity = provider.name
        claim_scope = providers.CLAIM_HARNESS_VERIFICATION
        seed_policy = "fixed:scripted"
        model_version_note = "stub 1.0.0"
    else:
        if not args.model_identity:
            print("ERROR: --model-identity is required for the http backend", file=sys.stderr)
            return 2
        if not args.model:
            print("ERROR: --model is required for the http backend", file=sys.stderr)
            return 2
        seed = None if args.seed.strip().lower() in ("", "none") else int(args.seed)
        provider = providers.HTTPChatProvider(
            name=f"http:{args.model}", model=args.model, base_url=args.base_url,
            temperature=args.temperature, top_p=args.top_p, seed=seed)
        model_identity = args.model_identity
        claim_scope = providers.CLAIM_COGNITIVE_MEASUREMENT
        seed_policy = f"fixed:{seed}" if seed is not None else "provider-default"
        model_version_note = None  # noqa: F841 (kept for symmetry)

    # 5. Run: collect all cells and trial rows first (trial log is bound into receipts).
    os.makedirs(args.out, exist_ok=True)
    receipts_dir = os.path.join(args.out, "receipts")
    all_cells = []          # (vector, variant, cell)
    trial_rows = []
    for vid in case_ids:
        spec = vectors.get_vector(vid)
        result = runner.run_vector(
            spec, provider, prompts[spec.system_prompt_name], pos_list, args.n,
            temperature=args.temperature, top_p=args.top_p, seed_policy=seed_policy,
            interposition_state=runner.INTERPOSITION_DISABLED_SANDBOXED,
            max_output_tokens=args.max_output_tokens)
        for cell in result["cells"]:
            variant = next(v for v in spec.variants if v["id"] == cell["variant_id"])
            all_cells.append((spec, variant, cell))
            for trial in cell["n_trials_detail"]:
                trial_rows.append(runner.trial_log_entry(cell, trial))

    # 6. Trial log first (its sha256 is bound into every receipt).
    _, trial_log_sha256 = runner.write_trial_log(
        trial_rows, os.path.join(args.out, "trials.jsonl"))

    # 7. Receipts.
    if args.backend == "http":
        returned_label = getattr(provider, "provider_returned_model_label", None)
    else:
        returned_label = provider.name  # stub echoes its own name as its label
    status_counts = {runner.CELL_PASS: 0, runner.CELL_FINDING: 0, runner.CELL_INCOMPLETE: 0}
    n_written = 0
    for spec, variant, cell in all_cells:
        sibling_cells = [c for (s, v, c) in all_cells
                         if s.vector_id == spec.vector_id and v["id"] == variant["id"]]
        # Build one receipt per (vector, variant); dedupe via first cell.
        if cell is not sibling_cells[0]:
            continue
        receipt = runner.build_receipt(
            spec, variant, sibling_cells,
            model_identity=model_identity,
            provider_returned_model_label=returned_label,
            temperature=args.temperature, top_p=args.top_p, seed_policy=seed_policy,
            interposition_state=runner.INTERPOSITION_DISABLED_SANDBOXED,
            claim_scope=claim_scope,
            prompt_provenance=prov,
            trial_log_sha256=trial_log_sha256)
        runner.validate_receipt(receipt)
        path = runner.write_receipt(
            receipt, os.path.join(receipts_dir, f"{spec.vector_id}_{variant['id']}.json"))
        n_written += 1
        print(f"wrote {path}")
    for _, _, cell in all_cells:
        status_counts[cell["cell_status"]] += 1

    print(f"\nRun complete: {len(all_cells)} cells, {len(trial_rows)} trials, "
          f"{n_written} receipts.")
    print(f"Cell statuses: PASS={status_counts[runner.CELL_PASS]} "
          f"FINDING={status_counts[runner.CELL_FINDING]} "
          f"INCOMPLETE={status_counts[runner.CELL_INCOMPLETE]}")
    print(f"Trial log: {os.path.join(args.out, 'trials.jsonl')} "
          f"(sha256 {trial_log_sha256[:16]}...)")
    print(f"claim_scope={claim_scope}; prompt RUNNER sha256 "
          f"{prov['prompt_sha256']['RUNNER_SYSTEM'][:16]}..., REVIEW sha256 "
          f"{prov['prompt_sha256']['REVIEW_SYSTEM'][:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
