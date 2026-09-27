import copy
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from residual.core import ContractError, digest
from residual.program_control import ProgramControl


def pr(number, title, *, head="a"*40, body="", draft=False):
    return {
        "number": number,
        "title": title,
        "body": body,
        "draft": draft,
        "html_url": f"https://github.test/pull/{number}",
        "head": {"sha": head},
        "base": {"sha": "b"*40},
        "updated_at": "2026-09-27T00:00:00Z",
        "labels": [],
    }


def issue(number, title, *, body="", labels=None):
    return {
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.test/issues/{number}",
        "updated_at": "2026-09-27T00:00:00Z",
        "labels": [{"name": name} for name in (labels or [])],
    }


class FakeGitHub:
    def __init__(self, pulls, issues):
        self.pulls = pulls
        self.issues = issues

    def __call__(self, url, token=None):
        parsed = urlsplit(url)
        page = int(parse_qs(parsed.query)["page"][0])
        if page > 1:
            return []
        if parsed.path.endswith("/pulls"):
            return copy.deepcopy(self.pulls)
        if parsed.path.endswith("/issues"):
            return copy.deepcopy(self.issues)
        raise AssertionError(url)


def test_sync_tracks_all_sources_without_double_counting_pull_shadow(tmp_path):
    pulls = [
        pr(10, "fix(release): successor", body="Successor to #9"),
        pr(9, "fix(release): predecessor", draft=True),
    ]
    issues = [
        {**issue(10, "PR shadow"), "pull_request": {"url": "shadow"}},
        issue(20, "M6 research follow-up", labels=["research"]),
    ]
    control = ProgramControl(tmp_path)
    snapshot = control.sync("owner/repo", fetcher=FakeGitHub(pulls, issues))

    assert snapshot["summary"]["total"] == 3
    assert {item["item_id"] for item in snapshot["items"]} == {
        "GH-PR-0010", "GH-PR-0009", "GH-ISSUE-0020",
    }

    old = control.item("GH-PR-0009")
    new = control.item("GH-PR-0010")
    # Source wording is preserved as a relation hint but cannot itself close
    # or supersede another program item.
    assert old["state"] == "VERIFYING"
    assert old["superseded_by"] == []
    assert new["supersedes"] == []
    assert new["source_relation_hints"] == [{"kind": "supersedes", "target": "GH-PR-0009"}]
    relation = next(r for r in snapshot["relations"] if r["from"] == "GH-PR-0010")
    assert relation["authority"] == "source_hint"

    research = control.item("GH-ISSUE-0020")
    assert research["state"] == "RESEARCH_ONLY"
    assert research["v1_disposition"] == "RESEARCH_ONLY"


def test_github_sync_never_infers_closed_from_source_absence(tmp_path):
    control = ProgramControl(tmp_path)
    first = FakeGitHub([pr(10, "active work")], [])
    control.sync("owner/repo", fetcher=first)
    assert control.item("GH-PR-0010")["state"] == "READY"

    # A later GitHub inventory no longer contains the PR. RESIDUAL carries the
    # program item forward for owner reconciliation instead of fabricating CLOSED.
    control.sync("owner/repo", fetcher=FakeGitHub([], []))
    item = control.item("GH-PR-0010")
    assert item["source_open"] is False
    assert item["state"] == "HUMAN_ACTION_REQUIRED"
    assert item["owner_action_required"] is True
    assert control.current()["summary"]["total"] == 1


def test_head_bound_override_fails_closed_on_new_pr_head(tmp_path):
    control = ProgramControl(tmp_path)
    control.sync("owner/repo", fetcher=FakeGitHub([pr(42, "v1 release gate", head="a"*40)], []))
    control.set_item(
        "GH-PR-0042",
        {
            "state": "READY_FOR_OWNER_GATE",
            "v1_disposition": "V1_REQUIRED",
            "owner_action_required": True,
        },
        bind_head="current",
    )
    current = control.item("GH-PR-0042")
    assert current["state"] == "READY_FOR_OWNER_GATE"
    assert current["override_stale"] is False

    control.sync("owner/repo", fetcher=FakeGitHub([pr(42, "v1 release gate", head="c"*40)], []))
    changed = control.item("GH-PR-0042")
    assert changed["state"] == "HUMAN_ACTION_REQUIRED"
    assert changed["owner_action_required"] is True
    assert changed["override_stale"] is True
    assert "expected aaaaaaaaaa" in changed["next_action"]


def test_manual_item_and_authority_change_project_immediately(tmp_path):
    control = ProgramControl(tmp_path)
    control.sync("owner/repo", fetcher=FakeGitHub([], []))
    item_id = control.add_manual(
        "Owner decides D4 inclusion",
        state="HUMAN_ACTION_REQUIRED",
        disposition="V1_REQUIRED",
        workstream="RELEASE_CONTROL",
        priority="P0",
        next_action="Record INCLUDE or EXCLUDE",
        owner_action_required=True,
    )
    item = control.item(item_id)
    assert item["state"] == "HUMAN_ACTION_REQUIRED"
    assert control.dashboard()["summary"]["owner_actions"] == 1

    control.set_item(item_id, {"state": "CLOSED", "owner_action_required": False})
    assert control.item(item_id)["state"] == "CLOSED"
    assert control.dashboard()["summary"]["owner_actions"] == 0


def test_manual_supersession_relation_projects_immediately(tmp_path):
    control = ProgramControl(tmp_path)
    control.sync(
        "owner/repo",
        fetcher=FakeGitHub([pr(1, "old repair"), pr(2, "new repair")], []),
    )
    control.link("GH-PR-0002", "GH-PR-0001", "supersedes")
    assert control.item("GH-PR-0001")["state"] == "SUPERSEDED"
    assert control.item("GH-PR-0002")["supersedes"] == ["GH-PR-0001"]
    relation = next(r for r in control.current()["relations"] if r["kind"] == "supersedes")
    assert relation["authority"] == "program"


def test_owner_action_and_v1_dashboard_are_separate_from_github_open_state(tmp_path):
    control = ProgramControl(tmp_path)
    control.sync(
        "owner/repo",
        fetcher=FakeGitHub(
            [pr(7, "docs"), pr(8, "release receipt")],
            [issue(9, "ordinary backlog")],
        ),
    )
    control.set_item(
        "GH-PR-0008",
        {
            "v1_disposition": "V1_REQUIRED",
            "state": "READY_FOR_OWNER_GATE",
            "owner_action_required": True,
            "priority": "P0",
        },
        bind_head="current",
    )
    dashboard = control.dashboard()
    assert [x["item_id"] for x in dashboard["owner_actions"]] == ["GH-PR-0008"]
    assert "GH-PR-0008" in {x["item_id"] for x in dashboard["v1_critical"]}
    assert dashboard["summary"]["total"] == 3
    assert len(dashboard["all_items"]) == 3


def test_event_log_is_hash_chained_and_snapshots_are_retained(tmp_path):
    control = ProgramControl(tmp_path)
    first = control.sync("owner/repo", fetcher=FakeGitHub([pr(1, "one")], []))
    control.set_item("GH-PR-0001", {"priority": "P1"}, bind_head="current")
    lines = [json.loads(line) for line in control.events_path.read_text().splitlines()]
    assert len(lines) >= 2
    previous = "0" * 64
    for event in lines:
        assert event["previous"] == previous
        claimed = event["hash"]
        body = dict(event)
        body.pop("hash")
        assert digest(body) == claimed
        previous = claimed
    assert (control.snapshots / f"{first['snapshot_sha256']}.json").exists()



def test_program_seed_applies_head_bound_triage_relations_and_manual_gates(tmp_path):
    control = ProgramControl(tmp_path)
    control.sync(
        "owner/repo",
        fetcher=FakeGitHub([
            pr(476, "QD2 product", head="4"*40),
            pr(483, "F6 helper", head="8"*40),
        ], []),
    )
    seed = {
        "schema_version": "residual.program-seed.v1",
        "seed_id": "seed-test",
        "items": [
            {
                "item_id": "GH-PR-0476",
                "expected_head": "4"*40,
                "patch": {
                    "state": "VERIFYING",
                    "v1_disposition": "V1_REQUIRED",
                    "workstream": "PRODUCT_CANDIDATE",
                    "priority": "P0",
                },
            },
            {
                "item_id": "GH-PR-0483",
                "expected_head": "8"*40,
                "patch": {
                    "state": "VERIFYING",
                    "v1_disposition": "V1_REQUIRED",
                    "workstream": "AUD1_F6",
                    "priority": "P0",
                },
            },
        ],
        "relations": [
            {"from": "GH-PR-0483", "to": "GH-PR-0476", "kind": "depends_on"},
        ],
        "manual_items": [
            {
                "title": "Owner decides D4",
                "state": "HUMAN_ACTION_REQUIRED",
                "v1_disposition": "V1_REQUIRED",
                "workstream": "RELEASE_CONTROL",
                "priority": "P0",
                "owner_action_required": True,
            }
        ],
    }

    result = control.apply_seed(seed)
    assert result == {"items": 2, "relations": 1, "manual_items": 1, "already_applied": False}
    assert control.item("GH-PR-0476")["state"] == "VERIFYING"
    helper = control.item("GH-PR-0483")
    assert helper["depends_on"] == ["GH-PR-0476"]
    assert helper["state"] == "VERIFYING"
    assert control.item("GH-PR-0476")["blocked_by"] == []

    owner_items = control.dashboard()["owner_actions"]
    assert len(owner_items) == 1
    assert owner_items[0]["title"] == "Owner decides D4"

    repeated = control.apply_seed(seed)
    assert repeated == {"items": 2, "relations": 1, "manual_items": 1, "already_applied": True}
    assert len([x for x in control.current()["items"] if x["title"] == "Owner decides D4"]) == 1

    # The seed's HEAD-bound decision is not transferable to a successor head.
    control.sync(
        "owner/repo",
        fetcher=FakeGitHub([
            pr(476, "QD2 product", head="5"*40),
            pr(483, "F6 helper", head="8"*40),
        ], []),
    )
    product = control.item("GH-PR-0476")
    assert product["state"] == "HUMAN_ACTION_REQUIRED"
    assert product["override_stale"] is True



def test_seed_refuses_changed_expected_head_before_any_mutation(tmp_path):
    control = ProgramControl(tmp_path)
    control.sync(
        "owner/repo",
        fetcher=FakeGitHub([pr(476, "QD2 product", head="5"*40)], []),
    )
    before = control.current()["snapshot_sha256"]
    seed = {
        "schema_version": "residual.program-seed.v1",
        "seed_id": "stale-seed",
        "items": [{
            "item_id": "GH-PR-0476",
            "expected_head": "4"*40,
            "patch": {
                "state": "READY_FOR_OWNER_GATE",
                "v1_disposition": "V1_REQUIRED",
                "priority": "P0",
            },
        }],
        "relations": [],
        "manual_items": [],
    }
    with pytest.raises(ContractError, match="HEAD mismatch"):
        control.apply_seed(seed)
    assert control.current()["snapshot_sha256"] == before
    assert control.item("GH-PR-0476")["state"] == "READY"
    assert control.item("GH-PR-0476")["v1_disposition"] == "UNCLASSIFIED"

def test_seed_rejects_unknown_schema_and_requires_prior_sync(tmp_path):
    control = ProgramControl(tmp_path)
    with pytest.raises(ContractError):
        control.apply_seed({"schema_version": "wrong"})

    with pytest.raises(ContractError):
        control.apply_seed({
            "schema_version": "residual.program-seed.v1",
            "seed_id": "no-sync",
            "items": [],
            "relations": [],
            "manual_items": [],
        })


def test_program_cli_accepts_repo_after_sync_subcommand(tmp_path, monkeypatch, capsys):
    from residual import program_cli

    seen = {}

    class FakeControl:
        def __init__(self, root):
            seen["root"] = root

        def sync(self, repo, token=None):
            seen["repo"] = repo
            return {
                "snapshot_sha256": "a"*64,
                "inventory_sha256": "b"*64,
                "summary": {"total": 0},
            }

    monkeypatch.setattr(program_cli, "ProgramControl", FakeControl)
    assert program_cli.main([
        "--data", str(tmp_path),
        "sync",
        "--repo", "owner/repo",
        "--json",
    ]) == 0
    assert seen["repo"] == "owner/repo"
    output = capsys.readouterr().out
    assert '"snapshot_sha256"' in output

def test_invalid_mutations_fail_closed(tmp_path):
    control = ProgramControl(tmp_path)
    control.sync("owner/repo", fetcher=FakeGitHub([pr(1, "one")], []))
    with pytest.raises(ContractError):
        control.set_item("GH-PR-0001", {"state": "MADE_UP"})
    with pytest.raises(ContractError):
        control.link("GH-PR-0001", "GH-PR-0001", "supersedes")
    with pytest.raises(ContractError):
        control.sync("not a repo name", fetcher=FakeGitHub([], []))
