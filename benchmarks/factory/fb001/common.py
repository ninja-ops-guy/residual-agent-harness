from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Residual Benchmark",
    "GIT_AUTHOR_EMAIL": "benchmark@localhost",
    "GIT_COMMITTER_NAME": "Residual Benchmark",
    "GIT_COMMITTER_EMAIL": "benchmark@localhost",
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
}

EXPECTED = {
    "normalize_rule": "lowercase-dash-collapse",
    "retry_statuses": [408, 429, 500, 502, 503, 504],
    "backoff_seconds": [1, 2, 4, 8],
    "health_thresholds": {"healthy": 0.99, "degraded": 0.95},
    "label_order": "lexicographic-key",
    "timeout_budget_seconds": 30,
}

POLICY = {
    "backoff_seconds": EXPECTED["backoff_seconds"],
    "health_thresholds": EXPECTED["health_thresholds"],
    "label_order": EXPECTED["label_order"],
    "normalize_rule": EXPECTED["normalize_rule"],
    "retry_statuses": EXPECTED["retry_statuses"],
    "schema": "service-policy-v1",
    "timeout_budget_seconds": EXPECTED["timeout_budget_seconds"],
}

INPUT_COMMIT = "921c7d728fe9901ec5c5251509084917b9bd1b4b"
EXPECTED_OUTPUT_COMMIT = "beb95402f45815a9b68c06933dd419c476d0f132"

PROMPTS = {
    "normalize_rule": (
        "A service identifier policy requires ASCII lowercase, replacement of every run of non-alphanumeric "
        "characters with one dash, trimming dashes from both ends, and collapsing repeated dashes. "
        "Return the canonical strategy identifier exactly as JSON: {\"value\": \"...\"}. "
        "The allowed canonical identifier is lowercase-dash-collapse."
    ),
    "retry_statuses": (
        "For this benchmark, transient HTTP failures are defined exactly as request timeout, rate limit, "
        "and the standard retryable server/gateway statuses 500, 502, 503, 504. Return the ascending integer "
        "list as JSON: {\"value\": [...]}."
    ),
    "backoff_seconds": (
        "The retry policy starts at one second and doubles three times, with no jitter. Return all four delays "
        "as JSON: {\"value\": [...]}."
    ),
    "health_thresholds": (
        "Availability >= 0.99 is healthy. Availability >= 0.95 but below 0.99 is degraded. Return the two named "
        "thresholds as JSON: {\"value\": {\"healthy\": number, \"degraded\": number}}."
    ),
    "label_order": (
        "When rendering service labels, sort by label key using ordinary lexicographic ordering. Return the "
        "canonical policy identifier as JSON: {\"value\": \"...\"}. The identifier is lexicographic-key."
    ),
    "timeout_budget_seconds": (
        "The total service-check timeout budget is exactly thirty seconds. Return it as JSON: {\"value\": 30}."
    ),
}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], env=GIT_ENV, text=True).strip()


def _commit(root: Path, message: str) -> str:
    subprocess.check_call(["git", "-C", str(root), "add", "."], env=GIT_ENV)
    subprocess.check_call(["git", "-C", str(root), "commit", "-q", "-m", message], env=GIT_ENV)
    return git(root, "rev-parse", "HEAD")


def create_fixture(root: Path, *, known_good: bool = False) -> tuple[str, str | None]:
    root.mkdir(parents=True, exist_ok=False)
    subprocess.check_call(["git", "init", "-q", str(root)], env=GIT_ENV)
    (root / "README.md").write_text(
        "# FB001 Service Policy Fixture\n\nGenerate policy.json from six independently verifiable policy requirements.\n",
        encoding="utf-8",
    )
    input_commit = _commit(root, "fixture input")
    if input_commit != INPUT_COMMIT:
        raise RuntimeError(f"FB001 input commit drift: {input_commit}")
    output_commit = None
    if known_good:
        (root / "policy.json").write_text(
            json.dumps(POLICY, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        output_commit = _commit(root, "known good output")
        if output_commit != EXPECTED_OUTPUT_COMMIT:
            raise RuntimeError(f"FB001 output commit drift: {output_commit}")
    return input_commit, output_commit


def write_policy(root: Path, outputs: dict[str, object]) -> str:
    for key, expected in EXPECTED.items():
        if outputs.get(key) != expected:
            raise ValueError(f"incorrect benchmark output for {key}")
    (root / "policy.json").write_text(
        json.dumps(POLICY, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    return _commit(root, "known good output")
