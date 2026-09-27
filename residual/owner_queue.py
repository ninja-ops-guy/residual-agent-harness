"""Deterministic, fail-closed owner action queue.

The queue compresses already-verified machine state into explicit human decisions.
It never invents authorization and never treats a status summary as approval.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")
KINDS = {
    "maintainer_attestation",
    "research_freeze",
    "physical_intervention",
    "credential",
    "scope_decision",
    "exception",
}
PRIORITIES = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


class OwnerQueueError(ValueError):
    pass


@dataclass(frozen=True)
class OwnerAction:
    action_id: str
    title: str
    kind: str
    priority: str
    summary: str
    evidence: tuple[str, ...]
    command: str | None = None
    head_sha: str | None = None
    pr_number: int | None = None
    blocking: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "OwnerAction":
        required = ("action_id", "title", "kind", "priority", "summary", "evidence")
        missing = [k for k in required if k not in raw]
        if missing:
            raise OwnerQueueError(f"missing required fields: {', '.join(missing)}")
        kind = str(raw["kind"])
        priority = str(raw["priority"])
        if kind not in KINDS:
            raise OwnerQueueError(f"unknown owner action kind: {kind}")
        if priority not in PRIORITIES:
            raise OwnerQueueError(f"unknown priority: {priority}")
        evidence = raw["evidence"]
        if not isinstance(evidence, list) or not all(isinstance(v, str) and v.strip() for v in evidence):
            raise OwnerQueueError("evidence must be a non-empty-string array")
        head = raw.get("head_sha")
        if head is not None and not SHA40.fullmatch(str(head)):
            raise OwnerQueueError("head_sha must be an exact 40-character lowercase hex SHA")
        pr = raw.get("pr_number")
        if pr is not None and (not isinstance(pr, int) or pr <= 0):
            raise OwnerQueueError("pr_number must be a positive integer")
        command = raw.get("command")
        if kind == "maintainer_attestation":
            if head is None or pr is None:
                raise OwnerQueueError("maintainer_attestation requires exact head_sha and pr_number")
            expected = f"RESIDUAL-MAINTAINER-APPROVAL: {head}"
            if command != expected:
                raise OwnerQueueError("maintainer_attestation command must bind exactly to head_sha")
        if kind == "research_freeze" and not command:
            raise OwnerQueueError("research_freeze requires an explicit owner authorization phrase")
        return cls(
            action_id=str(raw["action_id"]),
            title=str(raw["title"]),
            kind=kind,
            priority=priority,
            summary=str(raw["summary"]),
            evidence=tuple(evidence),
            command=str(command) if command is not None else None,
            head_sha=str(head) if head is not None else None,
            pr_number=pr,
            blocking=bool(raw.get("blocking", True)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "title": self.title,
            "kind": self.kind,
            "priority": self.priority,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "command": self.command,
            "head_sha": self.head_sha,
            "pr_number": self.pr_number,
            "blocking": self.blocking,
        }


def load_actions(path: str | Path) -> list[OwnerAction]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise OwnerQueueError("owner queue input must be a JSON array")
    actions = [OwnerAction.from_dict(item) for item in raw if isinstance(item, dict)]
    if len(actions) != len(raw):
        raise OwnerQueueError("every owner queue entry must be an object")
    ids = [a.action_id for a in actions]
    if len(ids) != len(set(ids)):
        raise OwnerQueueError("duplicate action_id")
    return sorted(actions, key=lambda a: (PRIORITIES[a.priority], not a.blocking, a.action_id))


def render(actions: list[OwnerAction]) -> str:
    if not actions:
        return "OWNER ACTION QUEUE\n\nNo human actions required."
    out = ["OWNER ACTION QUEUE", ""]
    for a in actions:
        state = "BLOCKING" if a.blocking else "NON-BLOCKING"
        out.append(f"[{a.priority}] {a.title} — {state}")
        if a.pr_number:
            out.append(f"PR: #{a.pr_number}")
        if a.head_sha:
            out.append(f"HEAD: {a.head_sha}")
        out.append(a.summary)
        out.append("Evidence:")
        out.extend(f"- {line}" for line in a.evidence)
        if a.command:
            out.append("COPY:")
            out.append(a.command)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render fail-closed human authority actions")
    parser.add_argument("queue", help="JSON owner-action queue emitted by Station/research tooling")
    parser.add_argument("--json", action="store_true", help="emit canonical JSON instead of cards")
    args = parser.parse_args(argv)
    try:
        actions = load_actions(args.queue)
    except (OSError, json.JSONDecodeError, OwnerQueueError) as exc:
        print(f"owner-queue: invalid queue: {exc}")
        return 2
    if args.json:
        print(json.dumps([a.as_dict() for a in actions], sort_keys=True, separators=(",", ":")))
    else:
        print(render(actions), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
