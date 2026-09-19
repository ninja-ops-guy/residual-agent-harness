"""Declarative, bounded setup skills for documentation-driven integrations."""
from __future__ import annotations

import json
import re
import shlex
import urllib.parse
from dataclasses import dataclass
from importlib import resources
from typing import Any

from residual.core import ContractError, digest, identifier

_SAFE_VALUE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,95}$")


def _opaque(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SAFE_VALUE.fullmatch(value):
        raise ContractError(f"{name} must be an opaque identifier")
    return value


def _http_url(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) > 500:
        raise ContractError(f"{name} must be a URL")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ContractError(f"{name} must be an HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ContractError(f"{name} must not contain credentials, query, or fragment")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ContractError(f"{name} must use HTTPS unless it is loopback")
    return value.rstrip("/")


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    title: str
    category: str
    summary: str
    keywords: tuple[str, ...]
    docs: tuple[str, ...]
    inputs: tuple[dict[str, Any], ...]
    steps: tuple[dict[str, Any], ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillSpec":
        required = {
            "id", "title", "category", "summary", "keywords", "docs", "inputs", "steps"
        }
        if not isinstance(data, dict) or set(data) != required:
            raise ContractError("invalid wiki skill manifest shape")
        skill_id = identifier(data["id"])
        for name in ("title", "category", "summary"):
            if not isinstance(data[name], str) or not data[name].strip():
                raise ContractError(f"skill {name} is required")
        if not isinstance(data["keywords"], list) or not all(
            isinstance(x, str) and x.strip() for x in data["keywords"]
        ):
            raise ContractError("skill keywords must be strings")
        if not isinstance(data["docs"], list) or not all(
            isinstance(x, str) and x.strip() for x in data["docs"]
        ):
            raise ContractError("skill docs must be strings")
        if not isinstance(data["inputs"], list) or not all(
            isinstance(x, dict) for x in data["inputs"]
        ):
            raise ContractError("skill inputs must be objects")
        if not isinstance(data["steps"], list) or not all(
            isinstance(x, dict) for x in data["steps"]
        ):
            raise ContractError("skill steps must be objects")
        return cls(
            skill_id,
            data["title"].strip(),
            data["category"].strip(),
            data["summary"].strip(),
            tuple(x.lower() for x in data["keywords"]),
            tuple(data["docs"]),
            tuple(data["inputs"]),
            tuple(data["steps"]),
        )

    def public(self) -> dict:
        return {
            "id": self.skill_id,
            "title": self.title,
            "category": self.category,
            "summary": self.summary,
            "keywords": list(self.keywords),
            "docs": list(self.docs),
            "inputs": list(self.inputs),
        }


@dataclass(frozen=True)
class SkillPlan:
    skill_id: str
    title: str
    docs: tuple[str, ...]
    steps: tuple[dict[str, Any], ...]
    artifacts: tuple[dict[str, Any], ...]
    plan_hash: str

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "title": self.title,
            "docs": list(self.docs),
            "steps": list(self.steps),
            "artifacts": list(self.artifacts),
            "plan_hash": self.plan_hash,
        }


class SkillRegistry:
    """Loads only repository-shipped manifests; no dynamic skill code imports."""

    def __init__(self):
        self._skills: dict[str, SkillSpec] = {}
        root = resources.files("residual.wiki").joinpath("skill_manifests")
        for entry in sorted(root.iterdir(), key=lambda p: p.name):
            if not entry.name.endswith(".json"):
                continue
            spec = SkillSpec.from_dict(json.loads(entry.read_text("utf-8")))
            if spec.skill_id in self._skills:
                raise ContractError("duplicate wiki skill id")
            self._skills[spec.skill_id] = spec
        if not self._skills:
            raise ContractError("wiki skill registry is empty")

    @property
    def skills(self) -> tuple[SkillSpec, ...]:
        return tuple(self._skills[key] for key in sorted(self._skills))

    def get(self, skill_id: str) -> SkillSpec:
        if not isinstance(skill_id, str):
            raise ContractError("skill id is required")
        spec = self._skills.get(skill_id)
        if spec is None:
            raise ContractError("unknown wiki setup skill")
        return spec

    def recommend(self, query: str, *, limit: int = 4) -> tuple[SkillSpec, ...]:
        if not isinstance(query, str):
            raise ContractError("skill recommendation query must be text")
        text = query.lower()
        ranked = []
        for spec in self.skills:
            score = sum(1 for word in spec.keywords if word in text)
            if score:
                ranked.append((score, spec))
        ranked.sort(key=lambda row: (-row[0], row[1].skill_id))
        return tuple(spec for _, spec in ranked[:limit])

    def _inputs(self, spec: SkillSpec, supplied: dict[str, Any] | None) -> dict[str, str]:
        supplied = dict(supplied or {})
        declared = {row.get("name"): row for row in spec.inputs}
        if None in declared or any(not isinstance(key, str) for key in declared):
            raise ContractError("skill input declaration is invalid")
        unknown = set(supplied) - set(declared)
        if unknown:
            raise ContractError("unknown skill input: " + sorted(unknown)[0])

        out: dict[str, str] = {}
        for name, row in declared.items():
            required = bool(row.get("required", False))
            value = supplied.get(name)
            if value in (None, ""):
                if required:
                    raise ContractError("missing required skill input: " + name)
                continue
            kind = row.get("type", "opaque")
            if kind == "opaque":
                out[name] = _opaque(value, name)
            elif kind == "url":
                out[name] = _http_url(value, name)
            elif kind == "text":
                if not isinstance(value, str) or not value.strip() or len(value) > 240:
                    raise ContractError(f"{name} must be bounded text")
                out[name] = value.strip()
            else:
                raise ContractError("unsupported skill input type")
        return out

    def plan(self, skill_id: str, supplied: dict[str, Any] | None = None) -> SkillPlan:
        spec = self.get(skill_id)
        values = self._inputs(spec, supplied)
        steps: list[dict[str, Any]] = []
        for raw in spec.steps:
            if set(raw) - {"kind", "title", "detail", "target"}:
                raise ContractError("skill step contains unknown fields")
            step = dict(raw)
            if not isinstance(step.get("kind"), str) or not isinstance(
                step.get("title"), str
            ):
                raise ContractError("skill step is invalid")
            steps.append(step)

        artifacts: list[dict[str, Any]] = []
        if skill_id == "distributed-worker":
            station = values.get("station_url")
            project = values.get("project_id")
            if station and project:
                command = (
                    "RESIDUAL_WORKER_TOKEN='<set-in-shell>' "
                    "python -m residual.station.worker --station "
                    + shlex.quote(station)
                    + " --project "
                    + shlex.quote(project)
                )
                artifacts.append(
                    {
                        "kind": "command_preview",
                        "name": "runner-command",
                        "content": command,
                        "secret_notice": (
                            "Replace the placeholder locally; never paste worker tokens "
                            "into the wiki agent."
                        ),
                    }
                )
        elif skill_id == "module-development":
            package = values.get("package", "my_residual_module")
            class_name = values.get("class_name", "ExampleModule")
            artifacts.append(
                {
                    "kind": "toml",
                    "name": "pyproject-entry-point",
                    "content": (
                        '[project.entry-points."residual.modules"]\n'
                        + package
                        + ' = "'
                        + package
                        + ":"
                        + class_name
                        + '"\n'
                    ),
                }
            )
            artifacts.append(
                {
                    "kind": "command_preview",
                    "name": "module-validation",
                    "content": (
                        "residual-module validate "
                        + package
                        + ":"
                        + class_name
                        + " --source-root ."
                    ),
                }
            )
        elif skill_id in {"local-model", "openai-compatible"}:
            artifacts.append(
                {
                    "kind": "station_handoff",
                    "name": "model-workshop",
                    "target": "#models",
                    "detail": (
                        "Complete credentials and connection testing in the existing "
                        "Model Workshop; secrets are not accepted by wiki skills."
                    ),
                }
            )
        elif skill_id == "enterprise-pilot":
            artifacts.append(
                {
                    "kind": "checklist",
                    "name": "enterprise-pilot",
                    "content": (
                        "Use the enterprise pilot, governance, security-review, and "
                        "training documents as the authoritative onboarding checklist."
                    ),
                }
            )

        payload = {
            "skill_id": spec.skill_id,
            "values": values,
            "steps": steps,
            "artifacts": artifacts,
            "docs": list(spec.docs),
        }
        return SkillPlan(
            spec.skill_id,
            spec.title,
            spec.docs,
            tuple(steps),
            tuple(artifacts),
            digest(payload),
        )
