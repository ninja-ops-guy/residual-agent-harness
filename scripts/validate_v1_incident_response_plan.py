#!/usr/bin/env python3
"""Validate the RESIDUAL v1 incident-response exercise plan without executing actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "residual.v1-incident-response-plan.v1"
RELEASE = "v1.0.0"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_SCENARIOS = {
    "IR-CREDENTIAL-LEAK",
    "IR-DATABASE-CORRUPTION",
    "IR-RUNAWAY-WORK",
    "IR-HOST-COMPROMISE",
    "IR-EVIDENCE-BREACH",
}
REQUIRED_LIST_FIELDS = {
    "detection",
    "containment",
    "evidence_preservation",
    "recovery",
    "communications",
    "decision_points",
    "human_authorities",
    "forbidden_actions",
    "required_evidence",
    "exit_criteria",
}
FORBIDDEN_SECRET_KEYS = {
    "secret", "password", "token", "api_key", "private_key",
    "credential_value", "key_value",
}


class PlanError(ValueError):
    pass


def _require_nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanError(f"{path}: expected non-empty string")
    return value


def _require_nonempty_string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise PlanError(f"{path}: expected non-empty array")
    out: list[str] = []
    for index, item in enumerate(value):
        out.append(_require_nonempty_string(item, f"{path}[{index}]"))
    return out


def _walk_no_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_SECRET_KEYS:
                raise PlanError(f"{path}.{key}: secret-bearing key forbidden")
            _walk_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_no_secrets(child, f"{path}[{index}]")


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise PlanError("$: expected object")
    _walk_no_secrets(plan)

    if plan.get("schema") != SCHEMA:
        raise PlanError(f"$.schema: expected {SCHEMA!r}")
    if plan.get("release") != RELEASE:
        raise PlanError(f"$.release: expected {RELEASE!r}")
    if plan.get("execution_status") != "PLANNED":
        raise PlanError("$.execution_status: planning artifact must remain PLANNED")

    source_revision = _require_nonempty_string(plan.get("source_revision"), "$.source_revision")
    if not SHA40.fullmatch(source_revision):
        raise PlanError("$.source_revision: expected lowercase 40-hex Git commit")

    for field in ("plan_owner", "operations_owner", "security_owner", "evidence_root"):
        _require_nonempty_string(plan.get(field), f"$.{field}")

    scenarios = plan.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise PlanError("$.scenarios: expected non-empty array")

    seen: set[str] = set()
    for index, raw in enumerate(scenarios):
        path = f"$.scenarios[{index}]"
        if not isinstance(raw, dict):
            raise PlanError(f"{path}: expected object")
        scenario_id = _require_nonempty_string(raw.get("id"), f"{path}.id")
        if scenario_id in seen:
            raise PlanError(f"{path}.id: duplicate {scenario_id}")
        seen.add(scenario_id)
        _require_nonempty_string(raw.get("title"), f"{path}.title")
        _require_nonempty_string(raw.get("trigger"), f"{path}.trigger")
        for field in REQUIRED_LIST_FIELDS:
            _require_nonempty_string_list(raw.get(field), f"{path}.{field}")

        preservation = " ".join(raw["evidence_preservation"]).lower()
        if not any(term in preservation for term in ("retain", "preserve", "hash")):
            raise PlanError(f"{path}.evidence_preservation: must explicitly preserve evidence")
        if not raw["human_authorities"]:
            raise PlanError(f"{path}.human_authorities: human authority is required")
        if not raw["required_evidence"]:
            raise PlanError(f"{path}.required_evidence: retained evidence is required")

    missing = sorted(REQUIRED_SCENARIOS - seen)
    if missing:
        raise PlanError(f"$.scenarios: missing required scenarios {missing}")

    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema": "residual.v1-incident-response-plan-validation.v1",
        "status": "PASS",
        "source_revision": source_revision,
        "scenario_count": len(scenarios),
        "required_scenarios": sorted(REQUIRED_SCENARIOS),
        "plan_sha256": hashlib.sha256(canonical).hexdigest(),
        "execution_claim": "NONE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        result = validate_plan(plan)
        code = 0
    except (OSError, json.JSONDecodeError, PlanError) as exc:
        result = {
            "schema": "residual.v1-incident-response-plan-validation.v1",
            "status": "BLOCKED",
            "reason": str(exc),
            "execution_claim": "NONE",
        }
        code = 2

    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
