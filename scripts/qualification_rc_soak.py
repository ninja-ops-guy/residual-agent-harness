#!/usr/bin/env python3
"""Artifact-bound observation runner; COMPLETE is not a release qualification.

Run with an installed interpreter's -I flag from outside the checkout. The frozen
wheel must contain the reviewed workload adapter; this runner never installs it.
The adapter exports qualification_soak_step(profile, config), returning the
effective configuration, profile and cumulative completed workload counts.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.abc
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import sys
import time
import uuid
import zipfile
from dataclasses import dataclass
from types import MappingProxyType


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def snapshot(value):
    return json.loads(canonical(value))


def finite(value, minimum=0):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= minimum
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("invalid_numeric_input")
    return value


def plain_file(path: Path) -> Path:
    # Reject symlink/reparse ancestors as well as the leaf; do not resolve them away.
    path = path.absolute()
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked_path")
    if not path.is_file():
        raise ValueError("not_regular_file")
    return path


def strict_json(raw, limit=65536):
    if type(raw) is not bytes or len(raw) > limit:
        raise ValueError("json_size_limit")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate_json_key")
            value[key] = item
        return value
    def invalid_constant(_value):
        raise ValueError("nonfinite_json")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid_constant)
    except (UnicodeError, RecursionError):
        raise ValueError("invalid_json_encoding_or_depth") from None
    def bounded(item, depth=0):
        if depth > 16:
            raise ValueError("json_depth_limit")
        if type(item) in (dict, list):
            if len(item) > 1024:
                raise ValueError("json_collection_limit")
            for child in (item.values() if type(item) is dict else item):
                bounded(child, depth+1)
            if type(item) is dict:
                for key in item:
                    if len(key) > 256:
                        raise ValueError("json_key_limit")
        elif type(item) is str and len(item) > 4096:
            raise ValueError("json_string_limit")
        elif type(item) is int and not -(2**63) <= item < 2**63:
            raise ValueError("json_integer_limit")
        elif type(item) is float and not math.isfinite(item):
            raise ValueError("nonfinite_json")
    bounded(value)
    return value


def read_bounded(path, limit=65536):
    with plain_file(Path(path)).open("rb") as stream:
        raw = stream.read(limit+1)
    if len(raw) > limit:
        raise ValueError("file_size_limit")
    return raw


def read_config(path: Path) -> dict:
    value = strict_json(read_bounded(path))
    if type(value) is not dict:
        raise ValueError("configuration_not_object")
    canonical(value)
    return value


@dataclass(frozen=True)
class Policy:
    duration: float
    interval: float
    max_gap: float
    max_rss: int
    max_fds: int
    workload: tuple[str, ...]

    def __post_init__(self):
        for item in (self.duration, self.interval, self.max_gap):
            finite(item, 0.001)
        if not self.interval <= self.max_gap < self.duration or self.duration > 30 * 86400:
            raise ValueError("invalid_timing_policy")
        for item in (self.max_rss, self.max_fds):
            if type(item) is not int or item <= 0 or item > 2**63 - 1:
                raise ValueError("invalid_resource_limit")
        if (not self.workload or len(self.workload) > 32 or
                len(set(self.workload)) != len(self.workload) or
                any(not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", k) for k in self.workload)):
            raise ValueError("invalid_workload_profile")


def policy_requirements(value):
    """Strict externally supplied requirements, never inferred from a journal."""
    if isinstance(value, Policy):
        value = snapshot(value.__dict__)
    keys = {"duration", "interval", "max_gap", "max_rss", "max_fds", "workload"}
    if type(value) is not dict or set(value) != keys:
        raise ValueError("invalid_expected_policy")
    if type(value["workload"]) not in (list, tuple) or any(type(k) is not str for k in value["workload"]):
        raise ValueError("invalid_expected_policy")
    try:
        validated = Policy(**{**value, "workload": tuple(value["workload"])})
    except (ValueError, TypeError):
        raise ValueError("invalid_expected_policy") from None
    return snapshot(validated.__dict__)


def exact_fields(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError("missing_or_unknown_manifest_fields")


def require_digest(value, length=64):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{" + str(length) + "}", value):
        raise ValueError("malformed_expected_hash")
    return value


def declared_text(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}", value):
        raise ValueError("malformed_declared_fact")


def input_path(root, value):
    # Portable relative paths only; forbid traversal, drive/UNC/ADS and reserved names.
    if type(value) is not str or not 1 <= len(value) <= 240:
        raise ValueError("unsafe_manifest_path")
    for part in value.split("/"):
        if (not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]*", part) or
                part.endswith(".") or part.split(".")[0].upper() in
                {"CON", "PRN", "AUX", "NUL", *["COM"+str(i) for i in range(1,10)],
                 *["LPT"+str(i) for i in range(1,10)]}):
            raise ValueError("unsafe_manifest_path")
    return Path(root).absolute().joinpath(*value.split("/"))


@dataclass(frozen=True)
class SelectedManifest:
    """Caller-selected requirements, not approval or independently proved provenance."""
    path: Path
    root: Path
    sha256: str
    canonical_bytes: bytes

    def __post_init__(self):
        require_digest(self.sha256)
        value = strict_json(self.canonical_bytes)
        if canonical(value) != self.canonical_bytes or digest(self.canonical_bytes) != self.sha256:
            raise ValueError("selected_manifest_digest_mismatch")
        self.validate(value, self.root)

    @property
    def facts(self):
        return strict_json(self.canonical_bytes)

    @classmethod
    def load(cls, path, root, canonical_sha256):
        require_digest(canonical_sha256)
        value = strict_json(read_bounded(path))
        raw = canonical(value)
        if digest(raw) != canonical_sha256:
            raise ValueError("selected_manifest_digest_mismatch")
        selected = cls(Path(path).absolute(), Path(root).absolute(), canonical_sha256, raw)
        selected.verify_inputs()
        return selected

    @staticmethod
    def validate(value, root):
        exact_fields(value, ("schema", "source", "artifacts", "candidate_artifact", "configuration",
                             "profile", "runner", "adapter", "environment"))
        if value["schema"] != "residual.rc-soak.manifest.v1":
            raise ValueError("unsupported_manifest_version")
        exact_fields(value["source"], ("head", "tree"))
        for item in value["source"].values(): require_digest(item, 40)
        artifacts = value["artifacts"]
        if type(artifacts) is not list or not 1 <= len(artifacts) <= 32:
            raise ValueError("invalid_artifact_inventory")
        ids, paths = set(), set()
        for artifact in artifacts:
            exact_fields(artifact, ("id", "kind", "path", "sha256", "source"))
            declared_text(artifact["id"]); require_digest(artifact["sha256"])
            input_path(root, artifact["path"])
            if artifact["kind"] not in ("wheel", "blob") or artifact["source"] != value["source"]:
                raise ValueError("contradictory_artifact_source")
            if artifact["id"] in ids or artifact["path"].casefold() in paths:
                raise ValueError("duplicate_artifact_identity_or_path")
            ids.add(artifact["id"]); paths.add(artifact["path"].casefold())
        declared_text(value["candidate_artifact"])
        chosen = [a for a in artifacts if a["id"] == value["candidate_artifact"] and a["kind"] == "wheel"]
        if len(chosen) != 1:
            raise ValueError("candidate_artifact_missing")
        exact_fields(value["configuration"], ("path", "sha256", "canonical_sha256"))
        require_digest(value["configuration"]["canonical_sha256"])
        exact_fields(value["profile"], ("path", "sha256", "id"))
        if type(value["profile"]["id"]) is not str or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value["profile"]["id"]):
            raise ValueError("invalid_profile_identity")
        for descriptor in (value["configuration"], value["profile"]):
            input_path(root, descriptor["path"]); require_digest(descriptor["sha256"])
            if descriptor["path"].casefold() in paths:
                raise ValueError("contradictory_input_paths")
            paths.add(descriptor["path"].casefold())
        exact_fields(value["runner"], ("sha256",)); require_digest(value["runner"]["sha256"])
        exact_fields(value["adapter"], ("module", "sha256", "artifact_id"))
        require_digest(value["adapter"]["sha256"])
        if (type(value["adapter"]["module"]) is not str or
                not re.fullmatch(r"residual(?:\.[A-Za-z_][A-Za-z_0-9]*)+", value["adapter"]["module"]) or
                value["adapter"]["artifact_id"] != value["candidate_artifact"]):
            raise ValueError("contradictory_adapter_identity")
        env = value["environment"]
        exact_fields(env, ("os", "architecture", "python", "dependencies"))
        declared_text(env["os"]); declared_text(env["architecture"])
        exact_fields(env["python"], ("implementation", "version", "executable_sha256"))
        declared_text(env["python"]["implementation"]); declared_text(env["python"]["version"])
        require_digest(env["python"]["executable_sha256"])
        if type(env["dependencies"]) is not list or len(env["dependencies"]) > 256:
            raise ValueError("invalid_dependency_inventory")
        names = set()
        for dependency in env["dependencies"]:
            exact_fields(dependency, ("name", "version", "artifact_sha256"))
            declared_text(dependency["name"]); declared_text(dependency["version"])
            require_digest(dependency["artifact_sha256"])
            name = re.sub(r"[-_.]+", "-", dependency["name"]).lower()
            if name in names: raise ValueError("duplicate_dependency_identity")
            names.add(name)

    def verify_inputs(self):
        if digest(canonical(strict_json(read_bounded(self.path)))) != self.sha256:
            raise ValueError("selected_manifest_drift")
        facts = self.facts
        verified_json = {}
        for descriptor in [*facts["artifacts"], facts["configuration"], facts["profile"]]:
            limit = 256*1024*1024 if "kind" in descriptor else 65536
            raw = read_bounded(input_path(self.root, descriptor["path"]), limit)
            if digest(raw) != descriptor["sha256"]:
                raise ValueError("manifest_input_hash_mismatch")
            if "kind" not in descriptor:
                verified_json[descriptor["path"]] = raw
        # Parse precisely the bytes just verified; never reopen a substituted profile.
        config = strict_json(verified_json[facts["configuration"]["path"]])
        if type(config) is not dict:
            raise ValueError("configuration_not_object")
        if digest(canonical(config)) != facts["configuration"]["canonical_sha256"]:
            raise ValueError("manifest_configuration_mismatch")
        profile = strict_json(verified_json[facts["profile"]["path"]])
        exact_fields(profile, ("schema", "id", "configuration_sha256", "policy"))
        if (profile["schema"] != "residual.rc-soak.profile.v1" or profile["id"] != facts["profile"]["id"] or
                profile["configuration_sha256"] != facts["configuration"]["sha256"]):
            raise ValueError("contradictory_profile")
        return policy_requirements(profile["policy"])


class Binding:
    """Compare installed candidate package bytes with the frozen wheel, no extraction."""
    PREFIXES = ("residual", "ai_providers", "observation_layer")

    def __init__(self, artifact, expected_hash, installed_root, config, profile, commit, tree, *,
                 expected_configuration_sha256, expected_configuration_bytes_sha256):
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("invalid_artifact_hash")
        if any(not re.fullmatch(r"[0-9a-f]{40}", x) for x in (commit, tree)):
            raise ValueError("invalid_source_identity")
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", profile):
            raise ValueError("invalid_profile")
        self.artifact = plain_file(Path(artifact))
        self.root = Path(installed_root).absolute()
        self.config = plain_file(Path(config))
        self.expected_hash = expected_hash
        self.config_hash = require_digest(expected_configuration_sha256)
        self.config_bytes_hash = require_digest(expected_configuration_bytes_sha256)
        if (digest(read_bounded(self.config)) != self.config_bytes_hash or
                digest(canonical(read_config(self.config))) != self.config_hash):
            raise ValueError("expected_configuration_mismatch")
        self.selected_manifest = None
        self.profile = profile
        self.files = {}
        if self.artifact.stat().st_size > 256 * 1024 * 1024:
            raise ValueError("artifact_too_large")
        artifact_bytes = self.artifact.read_bytes()
        if digest(artifact_bytes) != expected_hash:
            raise ValueError("artifact_drift")
        sources = {}
        with zipfile.ZipFile(io.BytesIO(artifact_bytes)) as wheel:
            names = wheel.namelist()
            if len(names) != len(set(names)) or len(names) > 100000:
                raise ValueError("ambiguous_wheel")
            total = 0
            for entry in wheel.infolist():
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
                    raise ValueError("unsafe_wheel_member")
                if path.parts and path.parts[0] in self.PREFIXES and not entry.is_dir():
                    total += entry.file_size
                    if total > 256 * 1024 * 1024 or path.suffix in (".pyc", ".pyo", ".pyd", ".so"):
                        raise ValueError("unsupported_runtime_inventory")
                    if entry.file_size > 64 * 1024 * 1024 or stat.S_ISLNK(entry.external_attr >> 16):
                        raise ValueError("unsupported_wheel_member")
                    data = wheel.read(entry)
                    self.files[entry.filename] = digest(data)
                    if path.suffix == ".py":
                        sources[entry.filename] = data
        if "residual/__init__.py" not in self.files:
            raise ValueError("candidate_package_missing")
        self.sources = MappingProxyType(sources)
        self.identity = {"artifact_sha256": expected_hash, "configuration_sha256": self.config_hash,
                         "profile": profile, "source_commit": commit, "source_tree": tree,
                         "installed_root": str(self.root), "python": sys.executable,
                         "runner_sha256": digest(Path(__file__).read_bytes()),
                         "execution_mode": "verified_source_snapshot",
                         "configuration_bytes_sha256": self.config_bytes_hash,
                         "rc_qualified": False,
                         "provenance_status": "not_independently_established",
                         "external_attestation_status": "not_established",
                         "prerequisite_authority_status": "not_established"}

    @classmethod
    def from_selected_manifest(cls, selected, installed_root):
        if type(selected) is not SelectedManifest:
            raise ValueError("externally_selected_manifest_required")
        selected.verify_inputs()
        facts = selected.facts
        if digest(Path(__file__).read_bytes()) != facts["runner"]["sha256"]:
            raise ValueError("expected_runner_mismatch")
        candidate = next(a for a in facts["artifacts"] if a["id"] == facts["candidate_artifact"])
        binding = cls(input_path(selected.root, candidate["path"]), candidate["sha256"], installed_root,
                      input_path(selected.root, facts["configuration"]["path"]), facts["profile"]["id"],
                      facts["source"]["head"], facts["source"]["tree"],
                      expected_configuration_sha256=facts["configuration"]["canonical_sha256"],
                      expected_configuration_bytes_sha256=facts["configuration"]["sha256"])
        module = facts["adapter"]["module"].replace(".", "/")
        matches = [p for p in (module+".py", module+"/__init__.py") if p in binding.sources]
        if len(matches) != 1 or digest(binding.sources[matches[0]]) != facts["adapter"]["sha256"]:
            raise ValueError("expected_adapter_mismatch")
        binding.selected_manifest = selected
        binding.identity.update({"manifest_sha256": selected.sha256,
                                 "profile_bytes_sha256": facts["profile"]["sha256"],
                                 "adapter_module": facts["adapter"]["module"],
                                 "adapter_sha256": facts["adapter"]["sha256"],
                                 "declared_environment_sha256": digest(canonical(facts["environment"])),
                                 "declared_environment_status": "declaration_only"})
        return binding

    def verify_artifact(self):
        hasher = hashlib.sha256()
        with plain_file(self.artifact).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(block)
        if hasher.hexdigest() != self.expected_hash:
            raise ValueError("artifact_drift")

    def validate_installation(self):
        if self.selected_manifest is not None:
            self.selected_manifest.verify_inputs()
        self.verify_artifact()
        if (digest(read_bounded(self.config)) != self.config_bytes_hash or
                digest(canonical(read_config(self.config))) != self.config_hash):
            raise ValueError("configuration_drift")
        actual = set()
        for prefix in self.PREFIXES:
            directory = self.root / prefix
            if directory.exists():
                for path in directory.rglob("*"):
                    if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                        raise ValueError("linked_runtime_inventory")
                    if path.is_file():
                        actual.add(path.relative_to(self.root).as_posix())
        if actual != set(self.files):
            raise ValueError("runtime_inventory_mismatch")
        for name, expected in self.files.items():
            if digest(plain_file(self.root / name).read_bytes()) != expected:
                raise ValueError("installed_bytes_drift")

    def admit(self, adapter, search_path):
        """Nonexecuting admission. Executed candidate code comes from frozen bytes.

        The filesystem can change after admission. The snapshot loader prevents
        that substitution becoming candidate Python code; periodic checks still
        reject installed drift. This is not filesystem immutability/provenance.
        """
        if self.selected_manifest is not None and adapter != self.selected_manifest.facts["adapter"]["module"]:
            raise ValueError("selected_adapter_override")
        self.check_search_path(search_path)
        self.validate_installation()
        name = adapter.replace(".", "/")
        if name + ".py" not in self.sources and name + "/__init__.py" not in self.sources:
            raise ValueError("adapter_not_in_frozen_inventory")
        if any(n.split(".")[0] in self.PREFIXES for n in sys.modules):
            raise ValueError("candidate_already_loaded")
        # Compile all selected Python modules without executing them.
        for path, source in self.sources.items():
            compile(source, str(self.root / path), "exec", dont_inherit=True)
        return SnapshotImporter(self)

    def observe(self, modules=None):
        self.validate_installation()
        origins = {}
        for name, module in list((sys.modules if modules is None else modules).items()):
            if name.split(".")[0] not in self.PREFIXES:
                continue
            origin = getattr(module, "__file__", None)
            if not origin:
                raise ValueError("runtime_origin_missing")
            path = plain_file(Path(origin))
            cached = getattr(module, "__cached__", None)
            if cached and Path(cached).exists():
                raise ValueError("cached_runtime_not_supported")
            try:
                relative = path.relative_to(self.root).as_posix()
            except ValueError:
                raise ValueError("checkout_shadowing") from None
            if relative not in self.files or digest(path.read_bytes()) != self.files[relative]:
                raise ValueError("runtime_origin_mismatch")
            # Namespace/package search locations cannot point into a checkout either.
            for location in getattr(module, "__path__", ()):
                if Path(location).absolute() != path.parent:
                    raise ValueError("package_search_path_drift")
            origins[name] = {"path": str(path), "sha256": self.files[relative]}
        if not origins or "residual" not in origins:
            raise ValueError("runtime_not_loaded")
        return {"identity": snapshot(self.identity), "origins": origins}

    def check_search_path(self, search_path):
        # -I suppresses cwd/PYTHONPATH, but site .pth files can still add a checkout.
        for location in search_path:
            if not location:
                raise ValueError("unsafe_import_search_path")
            path = Path(location).absolute()
            if path.is_dir() and any((path / prefix).exists() for prefix in self.PREFIXES):
                if path != self.root:
                    raise ValueError("checkout_shadowing")
            elif path.is_file() and zipfile.is_zipfile(path):
                with zipfile.ZipFile(path) as archive:
                    if any(n.split("/")[0] in self.PREFIXES for n in archive.namelist()):
                        raise ValueError("archive_shadowing")


class SnapshotImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Candidate Python imports cannot reopen substituted source or bytecode."""
    def __init__(self, binding):
        self.root, self.sources = binding.root, binding.sources

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] not in Binding.PREFIXES:
            return None
        base = fullname.replace(".", "/")
        for relative, package in ((base + "/__init__.py", True), (base + ".py", False)):
            if relative in self.sources:
                spec = importlib.util.spec_from_loader(fullname, self, is_package=package)
                spec.origin = str(self.root / relative)
                spec.loader_state = relative
                return spec
        raise ImportError("candidate_module_not_admitted")

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        relative = module.__spec__.loader_state
        module.__file__ = str(self.root / relative)
        module.__cached__ = None
        if hasattr(module, "__path__"):
            module.__path__ = [str((self.root / relative).parent)]
        code = compile(self.sources[relative], module.__file__, "exec", dont_inherit=True)
        exec(code, module.__dict__)


class Continuity:
    """Finite state monitor; failure is sticky and cannot be reset/resumed."""
    def __init__(self, policy, identity, epoch):
        self.policy, self.identity, self.epoch = policy, snapshot(identity), snapshot(epoch)
        self.previous = None
        self.first = None
        self.first_failure = None
        self.count = 0

    def reject(self, reason):
        if self.first_failure is None:
            self.first_failure = {"reason": reason, "sample_index": self.count}
        return False

    def add(self, sample):
        if self.first_failure:
            return False
        try:
            # Retain no adapter-owned dictionaries, including nested identities.
            sample = snapshot({key: sample[key] for key in
                ("monotonic", "wall", "rss", "fds", "identity", "epoch", "alive", "counts", "origins")})
            for key in ("monotonic", "wall", "rss", "fds"):
                finite(sample[key])
            if sample["identity"] != self.identity or sample["epoch"] != self.epoch:
                return self.reject("identity_drift")
            if sample["alive"] is not True:
                return self.reject("interruption")
            origins = sample["origins"]
            if type(origins) is not dict or not origins:
                return self.reject("invalid_module_observation")
            for name, origin in origins.items():
                if (type(name) is not str or type(origin) is not dict or set(origin) != {"path", "sha256"} or
                        type(origin["path"]) is not str or type(origin["sha256"]) is not str or
                        not re.fullmatch(r"[0-9a-f]{64}", origin["sha256"])):
                    return self.reject("invalid_module_observation")
            if self.previous and any(origins.get(k) != v for k, v in self.previous["origins"].items()):
                return self.reject("module_origin_drift")
            counts = sample["counts"]
            if (set(counts) != set(self.policy.workload) or
                    any(type(v) is not int or not 0 <= v <= 2**63 - 1 for v in counts.values())):
                return self.reject("invalid_workload_observation")
            if sample["rss"] > self.policy.max_rss or sample["fds"] > self.policy.max_fds:
                return self.reject("resource_limit")
            if self.previous:
                gap = sample["monotonic"] - self.previous["monotonic"]
                wall_gap = sample["wall"] - self.previous["wall"]
                if gap <= 0 or wall_gap <= 0:
                    return self.reject("clock_reset")
                if gap > self.policy.max_gap or wall_gap > self.policy.max_gap or abs(gap-wall_gap) > 1:
                    return self.reject("observation_gap")
                if any(counts[k] <= self.previous["counts"][k] for k in counts):
                    return self.reject("workload_stalled_or_reset")
            else:
                self.first = sample
            self.previous = sample
            self.count += 1
            return True
        except (KeyError, TypeError, ValueError, OverflowError):
            return self.reject("invalid_observation")

    def complete(self):
        if self.first_failure or self.count < 3:
            return False
        return all(self.previous[k] - self.first[k] >= self.policy.duration for k in ("wall", "monotonic"))


def validate_observations(raw, identity, epoch, expected_policy):
    """Replay required evidence; a completion-looking string is insufficient."""
    requirements = policy_requirements(expected_policy)
    policy_hash = digest(canonical(requirements))
    if not raw.endswith(b"\n") or len(raw) > 256 * 1024 * 1024:
        raise ValueError("invalid_evidence_length")
    rows = [json.loads(line) for line in raw.splitlines()]
    if not rows or any(canonical(row) != line for row, line in zip(rows, raw.splitlines())):
        raise ValueError("noncanonical_evidence")
    if any(row.get("seq") != i for i, row in enumerate(rows)):
        raise ValueError("evidence_sequence")
    start = rows[0]
    if (start.get("event") != "start" or start.get("identity") != identity or
            start.get("epoch") != epoch or start.get("rc_qualified") is not False):
        raise ValueError("evidence_identity")
    if (policy_requirements(start.get("policy")) != requirements or
            start.get("policy_sha256") != policy_hash):
        raise ValueError("evidence_policy_mismatch")
    values = dict(requirements)
    values["workload"] = tuple(values["workload"])
    monitor = Continuity(Policy(**values), identity, epoch)
    for row in rows[1:-1]:
        if row.get("event") != "sample" or not monitor.add(row):
            raise ValueError("evidence_observation")
    end = rows[-1]
    if (not monitor.complete() or end.get("event") != "provisional_completion" or
            end.get("sample_count") != monitor.count or end.get("rc_qualified") is not False):
        raise ValueError("evidence_incomplete")
    return {"identity": identity, "epoch": epoch, "sample_count": monitor.count,
            "policy_sha256": policy_hash, "observations_sha256": digest(raw), "bytes": len(raw)}


def validate_sealed(directory, identity, epoch, expected_policy):
    """Consumers MUST supply separately expected identity, epoch and policy.

    No cross-host authenticity, directory durability or privileged-writer
    protection is implied by a local hash seal.
    """
    path = Path(directory)
    if (path / "first-failure.json").exists():
        raise ValueError("failure_record_present")
    seal = json.loads(plain_file(path / "terminal-seal.json").read_bytes())
    revocation = path / "owned-seal-revocation.json"
    if revocation.exists():
        revoked = json.loads(plain_file(revocation).read_bytes())
        if revoked.get("owned_seal") == file_token(path / "terminal-seal.json"):
            raise ValueError("owned_seal_revoked")
    raw = plain_file(path / "observations.jsonl").read_bytes()
    expected = {"schema": "residual.soak.local-seal.v1", "rc_qualified": False,
                **validate_observations(raw, identity, epoch, expected_policy)}
    if seal != expected:
        raise ValueError("terminal_seal_mismatch")
    return expected


class Journal:
    """Exclusive local evidence; completion remains provisional until validated."""
    def __init__(self, directory):
        self.path = Path(directory).absolute()
        parent = self.path.parent
        for p in (parent, *parent.parents):
            info = p.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("unsafe_output_parent")
        self.path.mkdir(mode=0o700, exist_ok=False)
        self.stream = (self.path / "observations.jsonl").open("x", encoding="utf-8", newline="\n")
        self.failed = False
        self.first_failure = None
        self.sequence = 0
        self.hasher = hashlib.sha256()
        self.publication = None

    def write(self, record):
        line = canonical({**record, "seq": self.sequence}) + b"\n"
        written = self.stream.write(line.decode())
        if written != len(line.decode()):
            raise OSError("short_evidence_write")
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.hasher.update(line)
        self.sequence += 1

    def fail(self, reason, index):
        self.failed = True
        if self.first_failure is None:
            self.first_failure = {"event": "first_failure", "reason": reason, "sample_index": index}
        # Independent exclusive failure record, even if the observation stream broke.
        try:
            with (self.path / "first-failure.json").open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical(self.first_failure).decode() + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except (Exception, KeyboardInterrupt):
            pass  # Failure cannot manufacture a usable terminal seal.
        # Never unlink a terminal name: there is no portable conditional unlink.
        # Only invalidate a seal we demonstrably published and still recognize.
        # The failure sidecar already makes this run non-consumable.
        if self.publication is not None:
            try:
                target = self.path / "terminal-seal.json"
                if file_token(target) == self.publication:
                    with (self.path / "owned-seal-revocation.json").open("x", encoding="utf-8") as stream:
                        stream.write(canonical({"owned_seal": self.publication}).decode() + "\n")
                        stream.flush()
                        os.fsync(stream.fileno())
            except (Exception, KeyboardInterrupt):
                pass  # Never overwrite a competitor or remove retained evidence.
        if not self.stream.closed:
            try:
                self.write(self.first_failure)
            except (Exception, KeyboardInterrupt):
                pass

    def close(self):
        if not self.stream.closed:
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.stream.close()

    def publish(self, pending, target):
        before = file_token(pending)
        os.link(pending, target)
        # A failure/exception before return never establishes publication ownership.
        after = file_token(target)
        if before != after:
            raise ValueError("publication_identity_changed")
        return after

    def finalize(self, identity, epoch, expected_policy):
        if self.failed:
            raise ValueError("failed_journal")
        self.close()  # No acceptance marker exists if flush/fsync/close fails.
        raw = plain_file(self.path / "observations.jsonl").read_bytes()
        if digest(raw) != self.hasher.hexdigest():
            raise ValueError("evidence_changed_after_write")
        summary = validate_observations(raw, identity, epoch, expected_policy)
        seal = {"schema": "residual.soak.local-seal.v1", "rc_qualified": False, **summary}
        pending = self.path / "seal.pending.json"
        with pending.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical(seal).decode() + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        if json.loads(plain_file(pending).read_bytes()) != seal:
            raise ValueError("pending_seal_mismatch")
        if plain_file(self.path / "observations.jsonl").read_bytes() != raw:
            raise ValueError("evidence_changed_during_finalization")
        # Atomic exclusive name publication; never overwrite someone else's seal.
        # Unsupported hard-link filesystems fail closed. No power-loss guarantee.
        self.publication = self.publish(pending, self.path / "terminal-seal.json")
        return validate_sealed(self.path, identity, epoch, expected_policy)


def file_token(path):
    path = plain_file(Path(path))
    info = path.stat()
    return {"device": info.st_dev, "inode": info.st_ino, "bytes": info.st_size,
            "sha256": digest(path.read_bytes())}


def resources():
    status = Path(f"/proc/{os.getpid()}/status").read_text(encoding="utf-8")
    rss = next(int(line.split()[1]) * 1024 for line in status.splitlines() if line.startswith("VmRSS:"))
    return rss, len(list(Path(f"/proc/{os.getpid()}/fd").iterdir()))


def run(binding, policy, step, journal, *, clock=time.monotonic, wall=time.time,
        sleep=time.sleep, metrics=resources):
    monitor = None
    try:
        observed = binding.observe()
        identity = observed["identity"]
        epoch = {"run": uuid.uuid4().hex, "pid": os.getpid()}
        monitor = Continuity(policy, identity, epoch)
        journal.write({"event": "start", "identity": identity, "epoch": epoch,
                       "policy": policy_requirements(policy),
                       "policy_sha256": digest(canonical(policy_requirements(policy))), "rc_qualified": False})
        started = clock()
        while True:
            before = clock()
            # The adapter is frozen into the candidate. Health-only probes are insufficient.
            receipt = step(binding.profile, read_config(binding.config))
            rss, fds = metrics()
            observed = binding.observe()
            if (receipt["profile"] != binding.profile or
                    digest(canonical(receipt["effective_configuration"])) != binding.config_hash):
                raise ValueError("effective_configuration_drift")
            sample = {"identity": observed["identity"], "origins": observed["origins"],
                      "epoch": epoch, "monotonic": clock(), "wall": wall(),
                      "rss": rss, "fds": fds, "alive": True, "counts": snapshot(receipt["counts"])}
            if (sample["monotonic"] - before > policy.max_gap or
                    (monitor.count == 0 and sample["monotonic"] - started > policy.max_gap)):
                monitor.reject("observation_gap")
            accepted = monitor.add(sample)
            # Project only expected counters; untrusted receipt fields are never persisted.
            if not accepted:
                journal.fail(monitor.first_failure["reason"], monitor.count)
                return 1
            journal.write({"event": "sample", **monitor.previous})
            if monitor.complete():
                journal.write({"event": "provisional_completion", "rc_qualified": False,
                               "sample_count": monitor.count})
                journal.finalize(identity, epoch, policy)
                return 0
            sleep(policy.interval)
    except (Exception, KeyboardInterrupt):
        journal.fail("interrupted_or_observation_failed", 0 if monitor is None else monitor.count)
        return 1
    finally:
        try:
            journal.close()
        except (Exception, KeyboardInterrupt):
            journal.fail("evidence_close_failed", 0 if monitor is None else monitor.count)
            return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("manifest", "manifest-sha256", "inputs-root"):
        parser.add_argument("--" + key, required=True)
    for key in ("artifact", "sha256", "installed-root", "configuration", "profile", "commit", "tree", "adapter", "output-dir"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--interval", type=float, default=30)
    parser.add_argument("--max-gap", type=float, default=60)
    parser.add_argument("--max-rss", type=int, required=True)
    parser.add_argument("--max-fds", type=int, required=True)
    parser.add_argument("--workload", action="append", required=True)
    args = parser.parse_args(argv)
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        parser.error("isolated_interpreter_required: invoke python -I -B")
    if not re.fullmatch(r"residual(?:\.[a-zA-Z_][a-zA-Z_0-9]*)+", args.adapter):
        parser.error("candidate_adapter_required")
    try:
        policy = Policy(args.duration, args.interval, args.max_gap, args.max_rss, args.max_fds, tuple(args.workload))
        selected = SelectedManifest.load(args.manifest, args.inputs_root, args.manifest_sha256)
        facts = selected.facts
        candidate = next(a for a in facts["artifacts"] if a["id"] == facts["candidate_artifact"])
        if (args.commit != facts["source"]["head"] or args.tree != facts["source"]["tree"] or
                args.sha256 != candidate["sha256"] or args.adapter != facts["adapter"]["module"] or
                args.profile != facts["profile"]["id"] or
                Path(args.artifact).absolute() != input_path(selected.root, candidate["path"]) or
                Path(args.configuration).absolute() != input_path(selected.root, facts["configuration"]["path"]) or
                policy_requirements(policy) != selected.verify_inputs()):
            raise ValueError("caller_overrides_selected_manifest")
        binding = Binding.from_selected_manifest(selected, args.installed_root)
        importer = binding.admit(args.adapter, sys.path)
    except (Exception, KeyboardInterrupt):
        parser.error("invalid_binding_or_policy")
    journal = Journal(args.output_dir)
    sys.meta_path.insert(0, importer)
    try:
        module = importlib.import_module(args.adapter)
        binding.observe()
        step = module.qualification_soak_step
        if not callable(step) or step.__module__ != args.adapter:
            raise ValueError("adapter_origin_mismatch")
    except (Exception, KeyboardInterrupt):
        journal.fail("adapter_load_failed", 0)
        try:
            journal.close()
        except (Exception, KeyboardInterrupt):
            journal.fail("evidence_close_failed", 0)
        sys.meta_path.remove(importer)
        return 1
    previous = signal.getsignal(signal.SIGTERM)
    def interrupt(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    try:
        return run(binding, policy, step, journal)
    finally:
        signal.signal(signal.SIGTERM, previous)
        sys.meta_path.remove(importer)


if __name__ == "__main__":
    raise SystemExit(main())
