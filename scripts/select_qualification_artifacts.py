#!/usr/bin/env python3
"""Select one fail-closed Qualification-v1 producer artifact per logical producer.

This helper is intended for partial workflow reruns. Producer artifacts are expected
to be named:
    qualification-v1-<producer>-<40-hex source commit>-<run attempt>

For each logical producer, the greatest attempt not newer than --current-attempt is
selected. Older attempts remain eligible only when that producer was not rerun.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

EXPECTED_PRODUCERS = (
    "deterministic",
    "discovery",
    "m4",
    "artifacts",
    "browser-chromium",
    "browser-firefox",
    "browser-webkit",
    "concurrency",
    "protocol-fuzz",
    "toxic-provider",
    "active-workload",
    "browser-adversarial",
    "redteam",
    "windows",
    "fault-injection",
    "webvm-protocol-fuzz",
    "selftests",
    "active-http",
    "macos",
)


PRODUCER_JOBS = {
    producer: ({
        "windows": "windows-lifecycle",
        "macos": "macos-lifecycle",
        "selftests": "qualification-selftests",
        "active-http": "active-http-soak",
    }.get(producer, "browser" if producer in (
        "browser-chromium", "browser-firefox", "browser-webkit"
    ) else producer))
    for producer in EXPECTED_PRODUCERS
}


def validate_producer_results(results: dict[str, str]) -> None:
    """Require direct dependency results, including jobs with no uploaded artifact.

    GitHub retains untouched dependencies' successful results on partial reruns.
    Any failed/cancelled/skipped rerun invalidates aggregation even if an older
    PASS artifact survives. Browser's direct matrix result covers all children.
    """
    if not isinstance(results, dict):
        raise ValueError("producer results must be an object")
    expected = set(PRODUCER_JOBS.values())
    if set(results) != expected:
        raise ValueError(
            "producer result keys mismatch: missing="
            + repr(sorted(expected - set(results)))
            + "; unexpected=" + repr(sorted(set(results) - expected))
        )
    unsuccessful = {job: result for job, result in results.items() if result != "success"}
    if unsuccessful:
        raise ValueError("unsuccessful qualification producers: " + repr(unsuccessful))


@dataclass(frozen=True)
class ArtifactCandidate:
    producer: str
    attempt: int
    path: Path
    evidence_count: int


def _parse_name(name: str, expected_commit: str) -> tuple[str, int] | None:
    for producer in EXPECTED_PRODUCERS:
        prefix = f"qualification-v1-{producer}-"
        if not name.startswith(prefix):
            continue
        remainder = name[len(prefix):]
        match = re.fullmatch(r"([0-9a-f]{40})-([1-9][0-9]*)", remainder)
        if not match:
            raise ValueError(f"malformed qualification artifact name: {name}")
        commit, attempt_text = match.groups()
        if commit != expected_commit:
            raise ValueError(
                f"source commit mismatch for {name}: expected {expected_commit}, got {commit}"
            )
        return producer, int(attempt_text)
    if name.startswith("qualification-v1-"):
        raise ValueError(f"unexpected qualification producer artifact: {name}")
    return None


def _validate_payload(path: Path, expected_commit: str, attempt: int) -> int:
    for entry in path.rglob("*"):
        if entry.is_symlink():
            raise ValueError(f"{path.name}: symlinked artifact entry is not allowed: {entry}")
    evidence_paths = sorted(path.rglob("*.evidence.json"))
    if not evidence_paths:
        raise ValueError(f"{path.name}: no qualification evidence envelopes")
    for evidence_path in evidence_paths:
        try:
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(
                f"{path.name}: unreadable evidence envelope {evidence_path.name}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        source_commit = (payload.get("source") or {}).get("commit")
        if source_commit != expected_commit:
            raise ValueError(
                f"{path.name}: evidence source commit mismatch in {evidence_path.name}: "
                f"expected {expected_commit}, got {source_commit}"
            )
        ci = ((payload.get("environment") or {}).get("ci") or {})
        evidence_attempt = ci.get("GITHUB_RUN_ATTEMPT")
        if str(evidence_attempt) != str(attempt):
            raise ValueError(
                f"{path.name}: evidence run attempt mismatch in {evidence_path.name}: "
                f"expected {attempt}, got {evidence_attempt}"
            )
    return len(evidence_paths)


def discover_candidates(
    root: Path, expected_commit: str, current_attempt: int
) -> list[ArtifactCandidate]:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("--source-commit must be a lowercase 40-hex commit")
    if current_attempt < 1:
        raise ValueError("--current-attempt must be >= 1")
    if not root.is_dir():
        raise ValueError(f"artifact root is not a directory: {root}")

    candidates: list[ArtifactCandidate] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            raise ValueError(f"unexpected non-directory artifact payload: {path.name}")
        parsed = _parse_name(path.name, expected_commit)
        if parsed is None:
            continue
        producer, attempt = parsed
        if attempt > current_attempt:
            raise ValueError(
                f"{path.name}: future run attempt {attempt} exceeds current attempt {current_attempt}"
            )
        count = _validate_payload(path, expected_commit, attempt)
        candidates.append(ArtifactCandidate(producer, attempt, path, count))
    return candidates


def select_candidates(
    candidates: list[ArtifactCandidate], producer_results: dict[str, str]
) -> dict[str, ArtifactCandidate]:
    validate_producer_results(producer_results)
    by_producer: dict[str, list[ArtifactCandidate]] = {}
    for candidate in candidates:
        by_producer.setdefault(candidate.producer, []).append(candidate)

    missing = [producer for producer in EXPECTED_PRODUCERS if producer not in by_producer]
    if missing:
        raise ValueError("missing qualification producers: " + ", ".join(missing))

    unexpected = sorted(set(by_producer) - set(EXPECTED_PRODUCERS))
    if unexpected:
        raise ValueError("unexpected qualification producers: " + ", ".join(unexpected))

    selected: dict[str, ArtifactCandidate] = {}
    for producer in EXPECTED_PRODUCERS:
        rows = by_producer[producer]
        newest_attempt = max(row.attempt for row in rows)
        newest = [row for row in rows if row.attempt == newest_attempt]
        if len(newest) != 1:
            names = ", ".join(sorted(row.path.name for row in newest))
            raise ValueError(
                f"ambiguous qualification producer {producer} attempt {newest_attempt}: {names}"
            )
        selected[producer] = newest[0]
    return selected


def materialize_selection(
    selected: dict[str, ArtifactCandidate], output: Path, record: Path,
    *, context: dict | None = None
) -> None:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"selection output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    rows = []
    for producer in EXPECTED_PRODUCERS:
        candidate = selected[producer]
        destination = output / producer
        shutil.copytree(candidate.path, destination)
        rows.append(
            {
                "producer": producer,
                "attempt": candidate.attempt,
                "artifact_directory": candidate.path.name,
                "evidence_envelopes": candidate.evidence_count,
            }
        )

    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps({**(context or {}), "selected": rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select freshest source-bound Qualification-v1 producer artifacts"
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selection-record", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--current-attempt", type=int, required=True)
    parser.add_argument("--producer-results", required=True,
                        help="JSON object of exact direct-job results (not artifact-derived)")
    args = parser.parse_args(argv)

    try:
        results = json.loads(args.producer_results)
        validate_producer_results(results)
        candidates = discover_candidates(
            args.root, args.source_commit, args.current_attempt
        )
        selected = select_candidates(candidates, results)
        materialize_selection(selected, args.output, args.selection_record, context={
            "source_commit": args.source_commit,
            "current_attempt": args.current_attempt,
            "producer_results": results,
        })
    except Exception as exc:
        args.selection_record.parent.mkdir(parents=True, exist_ok=True)
        args.selection_record.write_text(json.dumps({
            "source_commit": args.source_commit,
            "current_attempt": args.current_attempt,
            "selection_failed": True,
            "error": f"{type(exc).__name__}: {exc}",
        }, indent=2) + "\n", encoding="utf-8")
        parser.exit(
            1,
            f"qualification artifact selection failed: {type(exc).__name__}: {exc}\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
