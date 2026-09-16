"""Frozen research-evidence bundles with source-bound metrics.

This module intentionally has no model/provider dependency. It turns retained
experiment artifacts into a deterministic manifest and derives table rows from
JSON Pointer values in those artifacts. Numeric claims therefore remain bound
to exact source bytes instead of being hand-copied into a manuscript.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class ResearchBundleError(ValueError):
    """A frozen evidence bundle is malformed, incomplete, or has drifted."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or relative.startswith(("/", "\\")):
        raise ResearchBundleError("artifact path must be a non-empty relative path")
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ResearchBundleError(f"artifact path escapes bundle root: {relative}") from exc
    if not candidate.is_file():
        raise ResearchBundleError(f"artifact is missing or not a regular file: {relative}")
    return candidate


def _pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def json_pointer(document: Any, pointer: str) -> Any:
    """Resolve RFC 6901-style JSON Pointer with strict missing-key handling."""
    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ResearchBundleError("metric pointer must be empty or begin with '/'")
    node = document
    for raw in pointer.split("/")[1:]:
        token = _pointer_token(raw)
        if isinstance(node, Mapping):
            if token not in node:
                raise ResearchBundleError(f"JSON Pointer key not found: {pointer}")
            node = node[token]
        elif isinstance(node, list):
            if token == "-" or not token.isdigit():
                raise ResearchBundleError(f"invalid array token in JSON Pointer: {pointer}")
            index = int(token)
            if index >= len(node):
                raise ResearchBundleError(f"JSON Pointer index out of range: {pointer}")
            node = node[index]
        else:
            raise ResearchBundleError(f"JSON Pointer traverses a scalar: {pointer}")
    return node


@dataclass(frozen=True)
class MetricSpec:
    name: str
    artifact: str
    pointer: str
    unit: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MetricSpec":
        allowed = {"name", "artifact", "pointer", "unit"}
        if not isinstance(value, Mapping) or set(value) - allowed:
            raise ResearchBundleError("metric spec contains unsupported fields")
        for key in ("name", "artifact", "pointer"):
            if not isinstance(value.get(key), str) or (key != "pointer" and not value[key]):
                raise ResearchBundleError(f"metric spec requires string field: {key}")
        unit = value.get("unit", "")
        if not isinstance(unit, str):
            raise ResearchBundleError("metric unit must be a string")
        return cls(value["name"], value["artifact"], value["pointer"], unit)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchBundleError(f"cannot parse JSON artifact: {path.name}") from exc


def freeze_bundle(root: str | Path, *, experiment_id: str, source_commit: str, artifacts: Sequence[str], metrics: Iterable[MetricSpec] = (), metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Create a deterministic manifest binding artifacts and extracted metrics."""
    root_path = Path(root)
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ResearchBundleError("experiment_id is required")
    if not isinstance(source_commit, str) or len(source_commit) < 7:
        raise ResearchBundleError("source_commit must identify a repository revision")
    if not isinstance(artifacts, Sequence) or isinstance(artifacts, (str, bytes)) or not artifacts:
        raise ResearchBundleError("at least one artifact is required")
    if len(artifacts) != len(set(artifacts)):
        raise ResearchBundleError("artifact paths must be unique")
    if metadata is not None:
        try:
            canonical_json(metadata)
        except (TypeError, ValueError) as exc:
            raise ResearchBundleError("metadata must contain finite JSON values") from exc

    records: list[dict[str, Any]] = []
    json_cache: dict[str, Any] = {}
    for relative in sorted(artifacts):
        path = _safe_path(root_path, relative)
        data = path.read_bytes()
        records.append({"path": relative, "size": len(data), "sha256": sha256_bytes(data)})

    metric_rows: list[dict[str, Any]] = []
    artifact_set = set(artifacts)
    seen_metric_names: set[str] = set()
    for spec in metrics:
        if not isinstance(spec, MetricSpec):
            raise ResearchBundleError("metrics must contain MetricSpec values")
        if spec.name in seen_metric_names:
            raise ResearchBundleError(f"duplicate metric name: {spec.name}")
        seen_metric_names.add(spec.name)
        if spec.artifact not in artifact_set:
            raise ResearchBundleError(f"metric source is not a frozen artifact: {spec.artifact}")
        if spec.artifact not in json_cache:
            json_cache[spec.artifact] = _load_json(_safe_path(root_path, spec.artifact))
        value = json_pointer(json_cache[spec.artifact], spec.pointer)
        try:
            canonical_json(value)
        except (TypeError, ValueError) as exc:
            raise ResearchBundleError(f"metric is not a finite JSON value: {spec.name}") from exc
        source_record = next(r for r in records if r["path"] == spec.artifact)
        metric_rows.append({"name": spec.name, "value": value, "unit": spec.unit, "source": {"artifact": spec.artifact, "artifact_sha256": source_record["sha256"], "pointer": spec.pointer}})

    payload: dict[str, Any] = {"schema_version": 1, "experiment_id": experiment_id, "source_commit": source_commit, "artifacts": records, "metrics": metric_rows, "metadata": dict(metadata or {})}
    payload["bundle_sha256"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    return payload


def verify_bundle(root: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute every binding and metric; return a compact verification receipt."""
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != 1:
        raise ResearchBundleError("unsupported bundle schema")
    artifact_records = manifest.get("artifacts")
    metric_records = manifest.get("metrics")
    if not isinstance(artifact_records, list) or not isinstance(metric_records, list):
        raise ResearchBundleError("bundle artifacts/metrics must be lists")
    expected_bundle_hash = manifest.get("bundle_sha256")
    unsigned = dict(manifest); unsigned.pop("bundle_sha256", None)
    computed_bundle_hash = sha256_bytes(canonical_json(unsigned).encode("utf-8"))
    if expected_bundle_hash != computed_bundle_hash:
        raise ResearchBundleError("manifest bundle hash mismatch")
    root_path = Path(root)
    by_path: dict[str, Mapping[str, Any]] = {}
    for record in artifact_records:
        if not isinstance(record, Mapping):
            raise ResearchBundleError("artifact record must be an object")
        relative = record.get("path")
        path = _safe_path(root_path, relative)
        if sha256_file(path) != record.get("sha256") or path.stat().st_size != record.get("size"):
            raise ResearchBundleError(f"artifact integrity mismatch: {relative}")
        if relative in by_path:
            raise ResearchBundleError(f"duplicate artifact record: {relative}")
        by_path[relative] = record
    json_cache: dict[str, Any] = {}
    for metric in metric_records:
        if not isinstance(metric, Mapping) or not isinstance(metric.get("source"), Mapping):
            raise ResearchBundleError("metric record is malformed")
        source = metric["source"]; relative = source.get("artifact")
        if relative not in by_path:
            raise ResearchBundleError("metric references an unfrozen artifact")
        if source.get("artifact_sha256") != by_path[relative].get("sha256"):
            raise ResearchBundleError("metric source digest does not match artifact record")
        if relative not in json_cache:
            json_cache[relative] = _load_json(_safe_path(root_path, relative))
        value = json_pointer(json_cache[relative], source.get("pointer"))
        if value != metric.get("value"):
            raise ResearchBundleError(f"metric value drift: {metric.get('name', '<unnamed>')}")
    return {"verified": True, "experiment_id": manifest.get("experiment_id"), "source_commit": manifest.get("source_commit"), "bundle_sha256": computed_bundle_hash, "artifact_count": len(artifact_records), "metric_count": len(metric_records)}


def render_metric_table(manifest: Mapping[str, Any]) -> str:
    """Render manuscript-ready Markdown directly from frozen metric rows."""
    metrics = manifest.get("metrics") if isinstance(manifest, Mapping) else None
    if not isinstance(metrics, list):
        raise ResearchBundleError("manifest metrics are unavailable")
    lines = ["| Metric | Value | Unit | Evidence |", "|---|---:|---|---|"]
    for metric in metrics:
        source = metric["source"]
        value = canonical_json(metric["value"])
        evidence = f"{source['artifact']} {source['artifact_sha256'][:12]} @ {source['pointer'] or '/'}"
        lines.append(f"| {metric['name']} | {value} | {metric.get('unit', '')} | `{evidence}` |")
    return "\n".join(lines) + "\n"


def load_spec(path: str | Path) -> dict[str, Any]:
    value = _load_json(Path(path))
    if not isinstance(value, dict):
        raise ResearchBundleError("bundle specification must be a JSON object")
    return value
