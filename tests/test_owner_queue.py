from pathlib import Path
import json

import pytest

from residual.owner_queue import OwnerAction, OwnerQueueError, load_actions, render


HEAD = "a" * 40


def test_attestation_is_exact_head_bound():
    action = OwnerAction.from_dict({
        "action_id": "pr-1",
        "title": "Approve PR",
        "kind": "maintainer_attestation",
        "priority": "P0",
        "summary": "All machine gates passed.",
        "evidence": ["tests pass"],
        "pr_number": 1,
        "head_sha": HEAD,
        "command": f"RESIDUAL-MAINTAINER-APPROVAL: {HEAD}",
    })
    assert action.command.endswith(HEAD)


def test_attestation_rejects_mismatched_command():
    with pytest.raises(OwnerQueueError):
        OwnerAction.from_dict({
            "action_id": "pr-1",
            "title": "Approve PR",
            "kind": "maintainer_attestation",
            "priority": "P0",
            "summary": "All machine gates passed.",
            "evidence": ["tests pass"],
            "pr_number": 1,
            "head_sha": HEAD,
            "command": "RESIDUAL-MAINTAINER-APPROVAL: " + ("b" * 40),
        })


def test_research_freeze_requires_explicit_phrase():
    with pytest.raises(OwnerQueueError):
        OwnerAction.from_dict({
            "action_id": "slm-00-freeze",
            "title": "Freeze SLM-00",
            "kind": "research_freeze",
            "priority": "P0",
            "summary": "Automated DAG complete.",
            "evidence": ["G PASS", "G2 PASS_WITH_NONBLOCKING_FINDINGS"],
        })


def test_queue_sort_and_render(tmp_path: Path):
    path = tmp_path / "queue.json"
    path.write_text(json.dumps([
        {
            "action_id": "later",
            "title": "Later",
            "kind": "scope_decision",
            "priority": "P2",
            "summary": "Later decision",
            "evidence": ["e"],
            "blocking": False,
        },
        {
            "action_id": "freeze",
            "title": "Freeze SLM-00",
            "kind": "research_freeze",
            "priority": "P0",
            "summary": "All automated lanes complete.",
            "evidence": ["G PASS", "G2 PASS_WITH_NONBLOCKING_FINDINGS"],
            "command": "freeze SLM-00",
        },
    ]))
    actions = load_actions(path)
    assert [a.action_id for a in actions] == ["freeze", "later"]
    text = render(actions)
    assert "COPY:\nfreeze SLM-00" in text
    assert "P0" in text
