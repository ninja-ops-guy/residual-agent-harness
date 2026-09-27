"""Initialize a RESIDUAL-RT Phase B pilot trial directory.

This helper prepares evidence; it does not call a model or execute any cyber action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research" / "residual_rt"
TEMPLATE = RESEARCH / "trial_manifest.template.json"
NOTES_TEMPLATE = RESEARCH / "investigation_notes.template.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def safe_slug(value: str) -> str:
    out = []
    for ch in value.lower():
        out.append(ch if ch.isalnum() else "-")
    slug = "-".join(part for part in "".join(out).split("-") if part)
    if not slug:
        raise ValueError("model produced empty trial slug")
    return slug[:80]


def init_trial(args) -> Path:
    trial_id = args.trial_id
    if not trial_id:
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        trial_id = f"PB-{date}-{safe_slug(args.model)}-r{args.repeats}"

    trial_dir = ROOT / "runs" / "residual-rt" / "trials" / trial_id
    if trial_dir.exists():
        raise FileExistsError(f"trial directory already exists: {trial_dir}")
    trial_dir.mkdir(parents=True)

    manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    manifest["trial_id"] = trial_id
    manifest["operator"] = args.operator
    manifest["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["source"]["branch_or_ref"] = git("rev-parse", "--abbrev-ref", "HEAD")
    manifest["source"]["commit_sha"] = git("rev-parse", "HEAD")
    manifest["source"]["working_tree_clean"] = not bool(git("status", "--porcelain"))

    manifest["provider"]["kind"] = args.kind
    manifest["provider"]["model"] = args.model
    manifest["provider"]["base_url"] = args.base_url
    manifest["provider"]["placement"] = args.placement
    manifest["sampling"]["repeats"] = args.repeats
    manifest["sampling"]["temperature"] = args.temperature
    manifest["sampling"]["seed_base"] = args.seed_base
    manifest["sampling"]["max_output_tokens"] = args.max_output_tokens

    manifest["environment"]["os"] = platform.platform()
    manifest["environment"]["python_version"] = sys.version.split()[0]

    paths = {
        "engagements": ROOT / manifest["artifacts"]["engagements_path"],
        "protocol": ROOT / manifest["artifacts"]["protocol_path"],
        "runner": ROOT / manifest["artifacts"]["runner_path"],
    }
    manifest["artifacts"]["engagements_sha256"] = sha256_file(paths["engagements"])
    manifest["artifacts"]["protocol_sha256"] = sha256_file(paths["protocol"])
    manifest["artifacts"]["runner_sha256"] = sha256_file(paths["runner"])

    result_rel = f"runs/residual-rt/trials/{trial_id}/phase-b.json"
    notes_rel = f"runs/residual-rt/trials/{trial_id}/investigation_notes.md"
    manifest["artifacts"]["result_path"] = result_rel
    manifest["artifacts"]["investigation_notes_path"] = notes_rel

    command = [
        "python", "-m", "residual.eval.residual_rt_models",
        "--engagements", "research/residual_rt/engagements.json",
        "--kind", args.kind,
        "--model", args.model,
        "--base-url", args.base_url,
        "--placement", args.placement,
        "--repeats", str(args.repeats),
        "--temperature", str(args.temperature),
        "--seed-base", str(args.seed_base),
        "--max-output-tokens", str(args.max_output_tokens),
        "--output", result_rel,
    ]
    if args.api_key_env:
        command += ["--api-key-env", args.api_key_env]
    manifest["execution"]["command"] = " ".join(command)

    (trial_dir / "trial_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    notes = NOTES_TEMPLATE.read_text(encoding="utf-8").replace(
        "Trial ID:\n", f"Trial ID: {trial_id}\n", 1
    )
    (trial_dir / "investigation_notes.md").write_text(notes, encoding="utf-8")
    (trial_dir / "RUN_COMMAND.txt").write_text(
        manifest["execution"]["command"] + "\n", encoding="utf-8"
    )
    return trial_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize, but do not execute, a RESIDUAL-RT Phase B pilot trial."
    )
    parser.add_argument("--trial-id")
    parser.add_argument("--operator", default="")
    parser.add_argument("--kind", choices=("ollama", "openai_compatible"), default="ollama")
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--placement", choices=("local", "remote"), default="local")
    parser.add_argument("--api-key-env")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed-base", type=int, default=20260918)
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    args = parser.parse_args()
    if args.repeats < 1 or args.max_output_tokens < 1:
        parser.error("repeats and max-output-tokens must be positive")
    if args.placement == "local" and not (
        args.base_url.startswith("http://127.0.0.1")
        or args.base_url.startswith("http://localhost")
        or args.base_url.startswith("http://[::1]")
        or args.base_url.startswith("https://127.0.0.1")
        or args.base_url.startswith("https://localhost")
        or args.base_url.startswith("https://[::1]")
    ):
        parser.error("local placement requires a loopback base URL")
    trial_dir = init_trial(args)
    print(trial_dir.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
