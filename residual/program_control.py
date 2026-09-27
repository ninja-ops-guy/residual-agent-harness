"""Evidence-bound program control for tracking RESIDUAL's own open work.

GitHub is an observational source. RESIDUAL program state is a separate,
explicitly governed projection with retained snapshots and local authority
overrides. Synchronization never closes an item merely because repository
metadata changed.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .core import ContractError, canonical, digest

SCHEMA_VERSION = "residual.program-control.v1"
OVERRIDE_VERSION = "residual.program-overrides.v1"

STATES = {
    "DISCOVERED",
    "TRIAGED",
    "READY",
    "RUNNING",
    "VERIFYING",
    "READY_FOR_OWNER_GATE",
    "BLOCKED",
    "HUMAN_ACTION_REQUIRED",
    "DEFERRED_POST_V1",
    "SUPERSEDED",
    "HISTORICAL_EVIDENCE",
    "RESEARCH_ONLY",
    "CLOSED",
    "ABANDONED",
}
DISPOSITIONS = {
    "V1_REQUIRED",
    "V1_SUPPORTING",
    "V1_EXCLUDED",
    "POST_V1",
    "RESEARCH_ONLY",
    "HISTORICAL",
    "UNCLASSIFIED",
}
PRIORITIES = {"P0", "P1", "P2", "P3"}
RELATION_KINDS = {"supersedes", "blocked_by", "depends_on", "related"}
TERMINAL_STATES = {"CLOSED", "SUPERSEDED", "HISTORICAL_EVIDENCE", "ABANDONED"}
MUTABLE_FIELDS = {
    "state",
    "v1_disposition",
    "workstream",
    "priority",
    "owner",
    "next_action",
    "owner_action_required",
    "notes",
}
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ITEM_RE = re.compile(r"^(?:GH-(?:PR|ISSUE)-\d{4,}|LOCAL-[A-F0-9]{8})$")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"program control state could not be read: {path.name}") from exc


def _validate_repo(repo: str) -> str:
    if not isinstance(repo, str) or not REPO_RE.fullmatch(repo):
        raise ContractError("repository must be owner/name")
    return repo


def _github_json(url: str, token: str | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "residual-program-control/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = f"GitHub returned HTTP {exc.code}"
        if exc.code == 403:
            detail += "; authentication or rate limit may be required"
        raise ContractError(detail) from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ContractError("GitHub inventory could not be retrieved") from exc


def _fetch_pages(
    repo: str,
    resource: str,
    *,
    token: str | None = None,
    fetcher: Callable[[str, str | None], Any] = _github_json,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, 51):
        query = urllib.parse.urlencode({"state": "open", "per_page": 100, "page": page})
        url = f"https://api.github.com/repos/{repo}/{resource}?{query}"
        value = fetcher(url, token)
        if not isinstance(value, list):
            raise ContractError(f"GitHub {resource} response must be an array")
        rows.extend(x for x in value if isinstance(x, dict))
        if len(value) < 100:
            break
    return rows


def _source_id(kind: str, number: int) -> str:
    prefix = "PR" if kind == "github_pr" else "ISSUE"
    return f"GH-{prefix}-{number:04d}"


def _body(item: dict[str, Any]) -> str:
    return str(item.get("body") or "")


def _labels(item: dict[str, Any]) -> list[str]:
    result = []
    for value in item.get("labels") or []:
        if isinstance(value, dict) and isinstance(value.get("name"), str):
            result.append(value["name"])
        elif isinstance(value, str):
            result.append(value)
    return result


def _extract_next_action(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"(?i)^(?:NEXT_ACTION|HUMAN_ACTION_REQUIRED|OWNER_ACTION_REQUIRED)\s*:\s*(.+)$", stripped)
        if match:
            return match.group(1).strip()[:600]
    return None


def _owner_gate(text: str) -> bool:
    return bool(re.search(
        r"(?im)\b(?:HUMAN_ACTION_REQUIRED|OWNER_ACTION_REQUIRED|OWNER GATE|OWNER AUTHORIZATION|OWNER RULING)\b",
        text,
    ))


def _proposed_disposition(title: str, body: str, labels: list[str]) -> str:
    text = f"{title}\n{body}\n{' '.join(labels)}".lower()
    if "[post-v1]" in text or "post-v1" in text or "after v1" in text:
        return "POST_V1"
    if "research" in labels or title.lower().startswith(("research:", "experiment:", "spec(m6)", "spec(m7)")):
        return "RESEARCH_ONLY"
    if "historical" in text or "[review only]" in text or "review-only" in text:
        return "HISTORICAL"
    if any(term in text for term in ("v1", "release", "aud-1", "f6", "qualification", "seal")):
        return "V1_SUPPORTING"
    return "UNCLASSIFIED"


def _workstream(title: str, body: str) -> str:
    text = f"{title}\n{body}".lower()
    rules = [
        ("CLAIM_CONTROL", ("claim", "documentation contradiction")),
        ("RELEASE_CONTROL", ("release receipt", "release gate", "release closure")),
        ("PRODUCT_CANDIDATE", ("convergence candidate", "qd-1", "qd-2")),
        ("AUD1_F6", ("aud-1", "f6")),
        ("SUPPLY_CHAIN", ("supply chain", "action pin", "dependency lock", "sbom", "provenance")),
        ("R4_SEAL", ("r4", "seal")),
        ("SHARED_COMMS", ("shared comms", "sc-mesh", "mesh")),
        ("DOGFOOD", ("dogfood",)),
        ("M7_SELF_IMPROVEMENT", ("m7", "self-improvement", "recursive")),
        ("M6_RESEARCH", ("m6", "improvementspec", "derivation graph", "metric registry")),
        ("WEBVM", ("webvm", "pages")),
    ]
    for name, tokens in rules:
        if any(token in text for token in tokens):
            return name
    return "BACKLOG"


def _proposed_state(title: str, body: str, draft: bool, disposition: str) -> str:
    text = f"{title}\n{body}"
    lower = text.lower()
    if _owner_gate(text):
        return "HUMAN_ACTION_REQUIRED"
    if re.search(r"(?im)^\s*(?:CURRENT_BLOCKER|BLOCKER)\s*:", text) or " blocked for v1 " in f" {lower} ":
        return "BLOCKED"
    if disposition == "POST_V1":
        return "DEFERRED_POST_V1"
    if disposition == "HISTORICAL":
        return "HISTORICAL_EVIDENCE"
    if disposition == "RESEARCH_ONLY":
        return "RESEARCH_ONLY"
    if draft and any(term in lower for term in ("qualification", "candidate", "review", "evidence", "gate")):
        return "VERIFYING"
    if draft:
        return "TRIAGED"
    return "READY"


def _priority(disposition: str, title: str) -> str:
    lower = title.lower()
    if disposition == "V1_REQUIRED":
        return "P0"
    if disposition == "V1_SUPPORTING" or any(term in lower for term in ("security", "release", "aud-1", "f6")):
        return "P1"
    if disposition in {"POST_V1", "RESEARCH_ONLY", "HISTORICAL"}:
        return "P3"
    return "P2"


def _explicit_refs(text: str) -> list[tuple[str, int]]:
    patterns = {
        "supersedes": r"(?i)\b(?:supersedes?|replaces?|successor to)\s+#(\d+)\b",
        "blocked_by": r"(?i)\bblocked by\s+#(\d+)\b",
        "depends_on": r"(?i)\b(?:depends on|requires)\s+#(\d+)\b",
    }
    found: list[tuple[str, int]] = []
    for kind, pattern in patterns.items():
        for raw in re.findall(pattern, text):
            found.append((kind, int(raw)))
    return found


def _normalize_pr(value: dict[str, Any]) -> dict[str, Any]:
    number = int(value["number"])
    title = str(value.get("title") or f"PR #{number}")
    body = _body(value)
    labels = _labels(value)
    head = ((value.get("head") or {}).get("sha"))
    base = ((value.get("base") or {}).get("sha"))
    disposition = _proposed_disposition(title, body, labels)
    state = _proposed_state(title, body, bool(value.get("draft")), disposition)
    return {
        "item_id": _source_id("github_pr", number),
        "title": title,
        "source": {
            "type": "github_pr",
            "number": number,
            "url": value.get("html_url") or value.get("url"),
            "head": head,
            "base": base,
            "draft": bool(value.get("draft")),
            "updated_at": value.get("updated_at"),
        },
        "source_open": True,
        "state": state,
        "v1_disposition": disposition,
        "workstream": _workstream(title, body),
        "priority": _priority(disposition, title),
        "owner": None,
        "next_action": _extract_next_action(body),
        "owner_action_required": _owner_gate(body),
        "notes": [],
        "labels": labels,
        "relation_hints": _explicit_refs(f"{title}\n{body}"),
        "override_stale": False,
    }


def _normalize_issue(value: dict[str, Any]) -> dict[str, Any]:
    number = int(value["number"])
    title = str(value.get("title") or f"Issue #{number}")
    body = _body(value)
    labels = _labels(value)
    disposition = _proposed_disposition(title, body, labels)
    state = _proposed_state(title, body, False, disposition)
    return {
        "item_id": _source_id("github_issue", number),
        "title": title,
        "source": {
            "type": "github_issue",
            "number": number,
            "url": value.get("html_url") or value.get("url"),
            "head": None,
            "base": None,
            "draft": False,
            "updated_at": value.get("updated_at"),
        },
        "source_open": True,
        "state": state,
        "v1_disposition": disposition,
        "workstream": _workstream(title, body),
        "priority": _priority(disposition, title),
        "owner": None,
        "next_action": _extract_next_action(body),
        "owner_action_required": _owner_gate(body),
        "notes": [],
        "labels": labels,
        "relation_hints": _explicit_refs(f"{title}\n{body}"),
        "override_stale": False,
    }


def _validate_patch(patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(patch, dict) or set(patch) - MUTABLE_FIELDS:
        raise ContractError("program item patch contains unsupported fields")
    result = dict(patch)
    if "state" in result and result["state"] not in STATES:
        raise ContractError("invalid program state")
    if "v1_disposition" in result and result["v1_disposition"] not in DISPOSITIONS:
        raise ContractError("invalid v1 disposition")
    if "priority" in result and result["priority"] not in PRIORITIES:
        raise ContractError("invalid priority")
    if "owner_action_required" in result and type(result["owner_action_required"]) is not bool:
        raise ContractError("owner_action_required must be boolean")
    for key in ("workstream", "owner", "next_action"):
        if key in result and result[key] is not None and not isinstance(result[key], str):
            raise ContractError(f"{key} must be a string or null")
    if "notes" in result and (
        not isinstance(result["notes"], list) or any(not isinstance(v, str) for v in result["notes"])
    ):
        raise ContractError("notes must be an array of strings")
    return result


class ProgramControl:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshots = self.root / "snapshots"
        self.snapshots.mkdir(exist_ok=True)
        self.current_path = self.root / "current.json"
        self.overrides_path = self.root / "overrides.json"
        self.events_path = self.root / "events.jsonl"

    def _overrides(self) -> dict[str, Any]:
        value = _load_json(
            self.overrides_path,
            {"schema_version": OVERRIDE_VERSION, "items": {}, "relations": [], "manual_items": []},
        )
        if not isinstance(value, dict) or value.get("schema_version") != OVERRIDE_VERSION:
            raise ContractError("program overrides have an unsupported schema")
        value.setdefault("items", {})
        value.setdefault("relations", [])
        value.setdefault("manual_items", [])
        return value

    def _event(self, kind: str, data: dict[str, Any]) -> None:
        previous = "0" * 64
        seq = 1
        if self.events_path.exists():
            lines = [line for line in self.events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                last = json.loads(lines[-1])
                previous = last["hash"]
                seq = int(last["seq"]) + 1
        event = {"seq": seq, "timestamp": _now(), "kind": kind, "data": data, "previous": previous}
        event["hash"] = digest(event)
        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(canonical(event) + "\n")

    def current(self) -> dict[str, Any]:
        value = _load_json(self.current_path, None)
        if value is None:
            return {
                "schema_version": SCHEMA_VERSION,
                "repo": None,
                "generated_at": None,
                "inventory_sha256": None,
                "previous_snapshot_sha256": None,
                "summary": {
                    "total": 0,
                    "active": 0,
                    "owner_actions": 0,
                    "v1_required": 0,
                    "v1_supporting": 0,
                    "unclassified": 0,
                    "states": {},
                    "dispositions": {},
                    "workstreams": {},
                },
                "relations": [],
                "items": [],
            }
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise ContractError("program snapshot has an unsupported schema")
        return value

    def set_item(
        self,
        item_id: str,
        patch: dict[str, Any],
        *,
        bind_head: str | None = None,
    ) -> dict[str, Any]:
        if not ITEM_RE.fullmatch(item_id):
            raise ContractError("invalid program item id")
        clean = _validate_patch(patch)
        overrides = self._overrides()
        current = next((x for x in self.current()["items"] if x["item_id"] == item_id), None)
        if current is None and not item_id.startswith("LOCAL-"):
            raise ContractError("program item was not found")
        if bind_head == "current":
            bind_head = (current or {}).get("source", {}).get("head")
            if not bind_head:
                raise ContractError("current item has no source head to bind")
        record = dict(overrides["items"].get(item_id) or {})
        record["patch"] = {**(record.get("patch") or {}), **clean}
        if bind_head is not None:
            if not isinstance(bind_head, str) or not re.fullmatch(r"[0-9a-f]{40}", bind_head):
                raise ContractError("bound head must be a lowercase 40-character Git SHA")
            record["expected_head"] = bind_head
        record["updated_at"] = _now()
        overrides["items"][item_id] = record
        _atomic_json(self.overrides_path, overrides)
        self._event("program.item_override", {"item_id": item_id, "patch": clean, "expected_head": record.get("expected_head")})
        return record

    def add_manual(
        self,
        title: str,
        *,
        state: str = "DISCOVERED",
        disposition: str = "UNCLASSIFIED",
        workstream: str = "BACKLOG",
        priority: str = "P2",
        next_action: str | None = None,
        owner_action_required: bool = False,
    ) -> str:
        if not isinstance(title, str) or not title.strip():
            raise ContractError("manual item title is required")
        if state not in STATES or disposition not in DISPOSITIONS or priority not in PRIORITIES:
            raise ContractError("manual item state, disposition, or priority is invalid")
        overrides = self._overrides()
        item_id = "LOCAL-" + uuid.uuid4().hex[:8].upper()
        overrides["manual_items"].append({
            "item_id": item_id,
            "title": title.strip()[:300],
            "source": {"type": "manual", "number": None, "url": None, "head": None, "base": None, "draft": False, "updated_at": _now()},
            "source_open": True,
            "state": state,
            "v1_disposition": disposition,
            "workstream": workstream,
            "priority": priority,
            "owner": None,
            "next_action": next_action,
            "owner_action_required": bool(owner_action_required),
            "notes": [],
            "labels": [],
            "relation_hints": [],
            "override_stale": False,
        })
        _atomic_json(self.overrides_path, overrides)
        self._event("program.manual_item_added", {"item_id": item_id, "title": title.strip()[:300]})
        return item_id

    def link(self, source: str, target: str, kind: str) -> None:
        if not ITEM_RE.fullmatch(source) or not ITEM_RE.fullmatch(target) or source == target:
            raise ContractError("program relation endpoints are invalid")
        if kind not in RELATION_KINDS:
            raise ContractError("invalid program relation kind")
        overrides = self._overrides()
        relation = {"from": source, "to": target, "kind": kind}
        if relation not in overrides["relations"]:
            overrides["relations"].append(relation)
            _atomic_json(self.overrides_path, overrides)
            self._event("program.relation_added", relation)

    def _apply_overrides(self, items: list[dict[str, Any]], overrides: dict[str, Any]) -> None:
        by_id = {item["item_id"]: item for item in items}
        for item_id, record in overrides["items"].items():
            item = by_id.get(item_id)
            if not item or not isinstance(record, dict):
                continue
            expected = record.get("expected_head")
            actual = item.get("source", {}).get("head")
            if expected is not None and actual != expected:
                item["override_stale"] = True
                item["state"] = "HUMAN_ACTION_REQUIRED"
                item["owner_action_required"] = True
                item["next_action"] = f"Reconcile stale authority override: expected {expected[:10]}, current {str(actual)[:10]}"
                item["notes"] = [*(item.get("notes") or []), "HEAD-bound program override did not transfer to the current source identity."]
                continue
            patch = _validate_patch(record.get("patch") or {})
            item.update(patch)

    def sync(
        self,
        repo: str,
        *,
        token: str | None = None,
        fetcher: Callable[[str, str | None], Any] = _github_json,
        progress: Callable[[str, int | None], None] | None = None,
    ) -> dict[str, Any]:
        repo = _validate_repo(repo)
        progress = progress or (lambda *_: None)
        progress("Fetching open pull requests", 10)
        pulls = _fetch_pages(repo, "pulls", token=token, fetcher=fetcher)
        progress("Fetching open issues", 35)
        issue_rows = _fetch_pages(repo, "issues", token=token, fetcher=fetcher)
        issues = [row for row in issue_rows if not row.get("pull_request")]

        items = [_normalize_pr(row) for row in pulls] + [_normalize_issue(row) for row in issues]
        overrides = self._overrides()
        items.extend(json.loads(json.dumps(overrides["manual_items"])))
        self._apply_overrides(items, overrides)

        number_map: dict[int, str] = {}
        for item in items:
            number = item.get("source", {}).get("number")
            if isinstance(number, int):
                current = number_map.get(number)
                if current is None or item["source"]["type"] == "github_pr":
                    number_map[number] = item["item_id"]

        relations: list[dict[str, str]] = []
        for item in items:
            for kind, number in item.pop("relation_hints", []):
                target = number_map.get(number)
                if target and target != item["item_id"]:
                    relation = {"from": item["item_id"], "to": target, "kind": kind}
                    if relation not in relations:
                        relations.append(relation)
        for relation in overrides["relations"]:
            if relation not in relations:
                relations.append(dict(relation))

        by_id = {item["item_id"]: item for item in items}
        for item in items:
            item["blocked_by"] = []
            item["depends_on"] = []
            item["supersedes"] = []
            item["superseded_by"] = []
            item["related"] = []

        for relation in relations:
            source = by_id.get(relation.get("from"))
            target = by_id.get(relation.get("to"))
            kind = relation.get("kind")
            if not source or not target or kind not in RELATION_KINDS:
                continue
            if kind == "supersedes":
                source["supersedes"].append(target["item_id"])
                target["superseded_by"].append(source["item_id"])
                if target["state"] not in TERMINAL_STATES:
                    target["state"] = "SUPERSEDED"
            elif kind == "blocked_by":
                source["blocked_by"].append(target["item_id"])
            elif kind == "depends_on":
                source["depends_on"].append(target["item_id"])
            else:
                source["related"].append(target["item_id"])
                target["related"].append(source["item_id"])

        for item in items:
            unresolved = [
                dep for dep in item["blocked_by"] + item["depends_on"]
                if dep in by_id and by_id[dep]["state"] not in TERMINAL_STATES
            ]
            if unresolved and item["state"] in {"DISCOVERED", "TRIAGED", "READY"}:
                item["state"] = "BLOCKED"
            item["active"] = item["state"] not in TERMINAL_STATES
            item["blocked_by"] = sorted(set(item["blocked_by"]))
            item["depends_on"] = sorted(set(item["depends_on"]))
            item["supersedes"] = sorted(set(item["supersedes"]))
            item["superseded_by"] = sorted(set(item["superseded_by"]))
            item["related"] = sorted(set(item["related"]))

        items.sort(key=lambda x: (
            {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(x["priority"], 9),
            x["workstream"],
            x["item_id"],
        ))
        relations.sort(key=lambda x: (x["kind"], x["from"], x["to"]))
        inventory = {
            "repo": repo,
            "items": items,
            "relations": relations,
        }
        inventory_sha = digest(inventory)
        previous = self.current()
        previous_sha = previous.get("snapshot_sha256")
        summary = self._summary(items)
        snapshot = {
            "schema_version": SCHEMA_VERSION,
            "repo": repo,
            "generated_at": _now(),
            "inventory_sha256": inventory_sha,
            "previous_snapshot_sha256": previous_sha,
            "summary": summary,
            "relations": relations,
            "items": items,
        }
        snapshot["snapshot_sha256"] = digest(snapshot)
        _atomic_json(self.current_path, snapshot)
        snapshot_path = self.snapshots / f"{snapshot['snapshot_sha256']}.json"
        if not snapshot_path.exists():
            _atomic_json(snapshot_path, snapshot)
        self._event("program.synced", {
            "repo": repo,
            "snapshot_sha256": snapshot["snapshot_sha256"],
            "inventory_sha256": inventory_sha,
            "pull_requests": len(pulls),
            "issues": len(issues),
        })
        progress("Program snapshot frozen", 100)
        return snapshot

    @staticmethod
    def _summary(items: list[dict[str, Any]]) -> dict[str, Any]:
        state_counts = Counter(item["state"] for item in items)
        disposition_counts = Counter(item["v1_disposition"] for item in items)
        workstreams = Counter(item["workstream"] for item in items if item.get("active"))
        return {
            "total": len(items),
            "active": sum(1 for item in items if item.get("active")),
            "owner_actions": sum(1 for item in items if item.get("active") and item.get("owner_action_required")),
            "v1_required": disposition_counts["V1_REQUIRED"],
            "v1_supporting": disposition_counts["V1_SUPPORTING"],
            "unclassified": disposition_counts["UNCLASSIFIED"],
            "states": dict(sorted(state_counts.items())),
            "dispositions": dict(sorted(disposition_counts.items())),
            "workstreams": dict(sorted(workstreams.items(), key=lambda kv: (-kv[1], kv[0]))),
        }

    def dashboard(self, limit: int = 200) -> dict[str, Any]:
        snapshot = self.current()
        items = snapshot["items"]
        active = [item for item in items if item.get("active")]
        owner = [item for item in active if item.get("owner_action_required")]
        critical = [
            item for item in active
            if item["v1_disposition"] in {"V1_REQUIRED", "V1_SUPPORTING"}
        ]
        order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        key = lambda item: (order.get(item.get("priority"), 9), item.get("workstream", ""), item["item_id"])
        return {
            "repo": snapshot.get("repo"),
            "generated_at": snapshot.get("generated_at"),
            "snapshot_sha256": snapshot.get("snapshot_sha256"),
            "inventory_sha256": snapshot.get("inventory_sha256"),
            "summary": snapshot["summary"],
            "owner_actions": sorted(owner, key=key)[:limit],
            "v1_critical": sorted(critical, key=key)[:limit],
            "active_items": sorted(active, key=key)[:limit],
            "workstreams": [
                {"name": name, "count": count}
                for name, count in snapshot["summary"].get("workstreams", {}).items()
            ],
        }

    def item(self, item_id: str) -> dict[str, Any]:
        item = next((x for x in self.current()["items"] if x["item_id"] == item_id), None)
        if item is None:
            raise ContractError("program item was not found")
        return item
