#!/usr/bin/env python3
"""Fail-closed validator for the RESIDUAL v1 deployment qualification profile."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_ID = "residual.v1-deployment-profile.v1"
RELEASE = "v1.0.0"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_SECRET_KEYS = {
    "secret", "password", "token", "api_key", "private_key",
    "credential", "credential_value", "key_value",
}


class ProfileError(ValueError):
    pass


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError(f"{path}: expected object")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ProfileError(f"{path}: expected non-empty array")
    return value


def _require_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{path}: expected non-empty string")
    if value == "UNDECIDED":
        raise ProfileError(f"{path}: UNDECIDED is fail-closed")
    return value


def _require_enum(value: Any, allowed: set[str], path: str) -> str:
    value = _require_str(value, path)
    if value not in allowed:
        raise ProfileError(f"{path}: expected one of {sorted(allowed)}, got {value!r}")
    return value


def _require_nonnegative_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProfileError(f"{path}: expected integer >= 0")
    return value


def _require_positive_int(value: Any, path: str) -> int:
    value = _require_nonnegative_int(value, path)
    if value == 0:
        raise ProfileError(f"{path}: expected integer > 0")
    return value


def _walk_no_undecided_or_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_SECRET_KEYS:
                raise ProfileError(f"{path}.{key}: secret-bearing key is forbidden")
            _walk_no_undecided_or_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_no_undecided_or_secrets(child, f"{path}[{index}]")
    elif value == "UNDECIDED":
        raise ProfileError(f"{path}: UNDECIDED is fail-closed")


def _validate_timestamp(value: Any, path: str) -> str:
    value = _require_str(value, path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProfileError(f"{path}: expected ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ProfileError(f"{path}: timezone offset is required")
    return value


def _is_loopback_address(value: str) -> bool:
    if value == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    _walk_no_undecided_or_secrets(profile)
    root = _require_dict(profile, "$")

    if root.get("schema") != SCHEMA_ID:
        raise ProfileError(f"$.schema: expected {SCHEMA_ID!r}")
    if root.get("release") != RELEASE:
        raise ProfileError(f"$.release: expected {RELEASE!r}")

    _require_str(root.get("profile_id"), "$.profile_id")
    _require_positive_int(root.get("profile_version"), "$.profile_version")
    _require_str(root.get("decision_owner"), "$.decision_owner")
    _require_str(root.get("operations_owner"), "$.operations_owner")
    _validate_timestamp(root.get("approval_timestamp"), "$.approval_timestamp")
    source_revision = _require_str(root.get("source_revision"), "$.source_revision")
    if not SHA40.fullmatch(source_revision):
        raise ProfileError("$.source_revision: expected lowercase 40-hex Git commit")

    network = _require_dict(root.get("network"), "$.network")
    exposure = _require_enum(
        network.get("station_exposure"),
        {"LOOPBACK_ONLY", "PRIVATE_NETWORK", "INTERNET_FACING"},
        "$.network.station_exposure",
    )
    bind_addresses = [
        _require_str(v, f"$.network.bind_addresses[{i}]")
        for i, v in enumerate(_require_list(network.get("bind_addresses"), "$.network.bind_addresses"))
    ]
    reverse_proxy = _require_dict(network.get("reverse_proxy"), "$.network.reverse_proxy")
    proxy_mode = _require_enum(
        reverse_proxy.get("mode"), {"NONE", "TRUSTED_PROXY"}, "$.network.reverse_proxy.mode"
    )
    tls = _require_enum(
        network.get("tls_termination"),
        {"NONE_LOCAL_ONLY", "STATION", "TRUSTED_PROXY"},
        "$.network.tls_termination",
    )
    proxy_header_trust = network.get("proxy_header_trust")
    cert_policy = _require_str(network.get("certificate_policy"), "$.network.certificate_policy")

    if exposure == "LOOPBACK_ONLY":
        bad = [value for value in bind_addresses if not _is_loopback_address(value)]
        if bad:
            raise ProfileError(f"$.network.bind_addresses: LOOPBACK_ONLY contains non-loopback {bad!r}")
    else:
        if tls == "NONE_LOCAL_ONLY":
            raise ProfileError("$.network.tls_termination: non-loopback exposure requires TLS")
        if cert_policy == "NOT_APPLICABLE":
            raise ProfileError("$.network.certificate_policy: non-loopback exposure requires certificate policy")

    if proxy_mode == "NONE":
        if proxy_header_trust != "NONE":
            raise ProfileError("$.network.proxy_header_trust: must be NONE without reverse proxy")
        if tls == "TRUSTED_PROXY":
            raise ProfileError("$.network.tls_termination: TRUSTED_PROXY requires reverse proxy")
    else:
        _require_str(reverse_proxy.get("name"), "$.network.reverse_proxy.name")
        _require_str(reverse_proxy.get("version"), "$.network.reverse_proxy.version")
        if proxy_header_trust == "NONE":
            raise ProfileError("$.network.proxy_header_trust: trusted proxy requires explicit header policy")
        _require_str(proxy_header_trust, "$.network.proxy_header_trust")

    remote_workers = _require_dict(network.get("remote_workers"), "$.network.remote_workers")
    remote_mode = _require_enum(
        remote_workers.get("mode"), {"DISALLOWED", "SUPPORTED"}, "$.network.remote_workers.mode"
    )
    if remote_mode == "SUPPORTED":
        _require_str(remote_workers.get("topology"), "$.network.remote_workers.topology")

    outbound = _require_dict(network.get("outbound_provider_access"), "$.network.outbound_provider_access")
    outbound_mode = _require_enum(
        outbound.get("mode"), {"DISALLOWED", "SUPPORTED"}, "$.network.outbound_provider_access.mode"
    )
    if outbound_mode == "SUPPORTED":
        _require_str(outbound.get("boundary"), "$.network.outbound_provider_access.boundary")

    tenancy = _require_dict(root.get("tenancy"), "$.tenancy")
    _require_enum(
        tenancy.get("operator_model"),
        {"SINGLE_TRUSTED_OPERATOR", "MULTI_OPERATOR"},
        "$.tenancy.operator_model",
    )
    user_model = _require_enum(
        tenancy.get("user_model"),
        {"LOCAL_OPERATOR_ONLY", "SINGLE_TENANT_MULTI_USER", "MULTI_TENANT"},
        "$.tenancy.user_model",
    )
    authz = _require_str(tenancy.get("authorization_boundary"), "$.tenancy.authorization_boundary")
    _require_str(tenancy.get("break_glass_authority"), "$.tenancy.break_glass_authority")
    _require_str(tenancy.get("credential_custody"), "$.tenancy.credential_custody")
    if user_model != "LOCAL_OPERATOR_ONLY" and authz == "NOT_APPLICABLE":
        raise ProfileError("$.tenancy.authorization_boundary: multi-user profile requires explicit policy")

    runtime = _require_dict(root.get("runtime"), "$.runtime")
    for field in ("operating_systems", "architectures", "python_versions", "filesystems"):
        values = _require_list(runtime.get(field), f"$.runtime.{field}")
        for i, value in enumerate(values):
            _require_str(value, f"$.runtime.{field}[{i}]")
    _require_enum(runtime.get("installation_artifact"), {"WHEEL", "CONTAINER"}, "$.runtime.installation_artifact")
    _require_str(runtime.get("sqlite_version"), "$.runtime.sqlite_version")
    _require_str(runtime.get("sqlite_durability_mode"), "$.runtime.sqlite_durability_mode")
    _require_str(runtime.get("persistent_volume_semantics"), "$.runtime.persistent_volume_semantics")
    multi_process = _require_enum(
        runtime.get("multi_process_station"), {"SUPPORTED", "DISALLOWED"}, "$.runtime.multi_process_station"
    )
    multi_host_db = _require_enum(
        runtime.get("multi_host_shared_database"),
        {"SUPPORTED", "DISALLOWED"},
        "$.runtime.multi_host_shared_database",
    )
    if multi_host_db == "SUPPORTED" and multi_process != "SUPPORTED":
        raise ProfileError("$.runtime: multi-host shared database requires multi-process Station support")

    objectives = _require_dict(root.get("objectives"), "$.objectives")
    _require_str(objectives.get("availability_slo"), "$.objectives.availability_slo")
    _require_positive_int(objectives.get("max_operation_recovery_seconds"), "$.objectives.max_operation_recovery_seconds")
    _require_nonnegative_int(objectives.get("rpo_seconds"), "$.objectives.rpo_seconds")
    _require_positive_int(objectives.get("rto_seconds"), "$.objectives.rto_seconds")
    _require_positive_int(objectives.get("backup_frequency_seconds"), "$.objectives.backup_frequency_seconds")
    _require_positive_int(objectives.get("backup_retention_seconds"), "$.objectives.backup_retention_seconds")
    _require_positive_int(objectives.get("evidence_retention_seconds"), "$.objectives.evidence_retention_seconds")
    _require_positive_int(objectives.get("log_retention_seconds"), "$.objectives.log_retention_seconds")
    _require_positive_int(objectives.get("log_disk_budget_bytes"), "$.objectives.log_disk_budget_bytes")
    host_loss = _require_enum(
        objectives.get("host_loss_claim"), {"NONE", "RESTORE_ONLY", "FAILOVER"}, "$.objectives.host_loss_claim"
    )
    region_loss = _require_enum(
        objectives.get("regional_loss_claim"), {"NONE", "RESTORE_ONLY", "FAILOVER"}, "$.objectives.regional_loss_claim"
    )
    _require_positive_int(objectives.get("soak_seconds"), "$.objectives.soak_seconds")
    _require_str(objectives.get("soak_environment"), "$.objectives.soak_environment")

    if region_loss != "NONE" and host_loss == "NONE":
        raise ProfileError("$.objectives: regional-loss claim requires a host-loss claim")
    if (host_loss == "FAILOVER" or region_loss == "FAILOVER") and multi_host_db != "SUPPORTED":
        raise ProfileError("$.objectives: failover claim requires multi-host shared database support")

    applicability = {
        "PR-G05": "REQUIRED" if exposure != "LOOPBACK_ONLY" else "NOT_APPLICABLE_BY_SCOPE",
        "PR-G09": "REQUIRED" if (multi_process == "SUPPORTED" or multi_host_db == "SUPPORTED") else "NOT_APPLICABLE_WITH_FAIL_CLOSED_ENFORCEMENT",
        "PR-G17": "REQUIRED" if (exposure == "INTERNET_FACING" or user_model != "LOCAL_OPERATOR_ONLY") else "NOT_APPLICABLE_BY_SCOPE",
        "PR-G31": "REQUIRED" if (host_loss != "NONE" or region_loss != "NONE") else "NOT_APPLICABLE_BY_SCOPE",
    }

    canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema": "residual.v1-deployment-profile-validation.v1",
        "status": "PASS",
        "profile_sha256": hashlib.sha256(canonical).hexdigest(),
        "source_revision": source_revision,
        "gate_applicability": applicability,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        result = validate_profile(profile)
    except (OSError, json.JSONDecodeError, ProfileError) as exc:
        result = {
            "schema": "residual.v1-deployment-profile-validation.v1",
            "status": "BLOCKED",
            "reason": str(exc),
        }
        payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 2

    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
