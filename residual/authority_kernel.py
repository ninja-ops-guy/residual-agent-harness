"""Authority kernel boundary and revision identity.

The authority kernel is every module whose code can allow or deny an
authority-relevant transition: if removing or altering the module could
change whether a coercion succeeds, it is in the kernel. (Boundary
proposed in REJECTION_PATH_MAPPING.md, "Kernel boundary proposal".)

kernel_revision() is a deterministic 64-hex digest over the exact bytes
of every kernel module plus the sha256 of the normative spec
(AUTH_INVARIANTS.md) the kernel was qualified against. Any kernel change
-- or any spec change -- yields a new revision, so qualification receipts
bound to a revision are never silently compared across revisions.

Fail-closed: a kernel that cannot be measured cannot be qualified.
Unreadable module files or an unresolvable spec raise instead of being
skipped.

Boundary adjustments vs. the proposal (each reviewed against the repo):
- ADDED residual/factory/evidence_receipts.py: WorkerReceipt issuance
  gate ("only passing decisions can issue") and StationIdentity.verify,
  which gates factory-handoff acceptance in measured_factory.py,
  acceptance_binding.py, and evidence_bus.py. Altering either changes
  whether forged-evidence coercion succeeds (EVD-001 at the factory
  boundary).
- ADDED residual/factory/evidence_bus.py: EvidenceBus.consumable()
  denies on invalid station signature, artifact-store mismatch, or
  unapproved stale receipts -- an authority gate over factory handoffs.
- EXCLUDED residual/authority.py (Track A2's typed-rejection vocabulary):
  it names rejection types but decides nothing; every module that raises
  them is already in the kernel.
- EXCLUDED verifier/extension modules (station/extensions.py,
  engine.py orchestration): evidence producers, each versioned
  per-verifier via verifier_revision on the receipt. The admission
  decisions they feed (station control/service, acceptance binding)
  are in the kernel.
- EXCLUDED residual/qualification/*: the qualification infrastructure
  measures the kernel; it is not the kernel. Including the measurer in
  the measured identity would be circular.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# Repo-relative paths of every module in the authority kernel.
KERNEL_MODULES: tuple[str, ...] = (
    "residual/quarantine.py",
    "residual/receipts.py",
    "residual/station/control.py",
    "residual/station/service.py",
    "residual/eval_frozen/acceptance_binding.py",
    "residual/factory/worker_contract.py",
    "residual/factory/evidence_receipts.py",
    "residual/factory/evidence_bus.py",
    "residual/goalspec.py",
    "residual/loop.py",
    "residual/brakes.py",
    "residual/gateway/gateway.py",
    "residual/iam/abac.py",
    "residual/iam/jit.py",
    "residual/telemetry/schema.py",
    "residual/factory/m4_sandbox.py",
    "residual/core.py",
    "scripts/check_maintainer_approval.py",
)

#: Spec filename, committed at the candidate repository root.
SPEC_FILENAME = "AUTH_INVARIANTS.md"


_PACKAGED_INPUT_NAMES = {
    SPEC_FILENAME: SPEC_FILENAME,
    "scripts/check_maintainer_approval.py": "check_maintainer_approval.py",
}


def _packaged_inputs() -> dict[str, Path]:
    """Resolve only the inert supplemental inputs bundled by this wheel.

    Presence selects packaged mode: incomplete/tampered resources never fall
    back to checkout, cwd, HOME, environment, or neighboring distribution files.
    The manifest is an integrity check, not an external trust root. Actual
    runtime modules are always read from REPO_ROOT, never from this bundle.
    """
    folder = REPO_ROOT / "residual" / "_authority_inputs"
    if not folder.exists() and not folder.is_symlink():
        return {}  # Source/editable installation; require its own root inputs.
    if folder.is_symlink() or not folder.is_dir():
        raise FileNotFoundError("packaged AUTH inputs must be a real directory")
    manifest_path = folder / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise FileNotFoundError("packaged AUTH input manifest missing or invalid")
    try:
        raw = manifest_path.read_bytes()
        if len(raw) > 4096:
            raise ValueError("oversized manifest")
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate manifest key")
                value[key] = item
            return value
        manifest = json.loads(raw, object_pairs_hook=unique)
        if (not isinstance(manifest, dict) or set(manifest) != {"schema", "sha256"}
                or manifest["schema"] != "residual.authority-inputs.v1"
                or not isinstance(manifest["sha256"], dict)
                or set(manifest["sha256"]) != set(_PACKAGED_INPUT_NAMES)):
            raise ValueError("invalid manifest shape")
        result = {}
        for relative, name in _PACKAGED_INPUT_NAMES.items():
            path = folder / name
            expected = manifest["sha256"][relative]
            if (not isinstance(expected, str) or len(expected) != 64
                    or any(c not in "0123456789abcdef" for c in expected)
                    or path.is_symlink() or not path.is_file()
                    or _sha256_file(path, what="packaged input") != expected):
                raise ValueError("missing or mismatched packaged AUTH input: " + relative)
            result[relative] = path
        return result
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise FileNotFoundError("packaged AUTH inputs cannot be measured") from exc


def spec_path() -> Path:
    """Return the normative spec belonging to this source tree or built wheel."""
    candidate = _packaged_inputs().get(SPEC_FILENAME, REPO_ROOT / SPEC_FILENAME)
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(
        f"normative spec {SPEC_FILENAME} missing from candidate tree; "
        "a kernel that cannot be measured against its spec cannot be qualified.")

def _sha256_file(path: Path, *, what: str) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise FileNotFoundError(
            f"authority kernel {what} unreadable: {path}") from exc
    return hashlib.sha256(data).hexdigest()


def revision(*, spec: Path | str | None = None) -> str:
    """Deterministic 64-hex identity of the exact authority kernel.

    sha256 over canonical JSON of {sorted "relpath:content-sha256" per
    kernel module, spec_hash}. Stable across runs on identical kernel
    code; any kernel-module or spec change yields a new revision.

    Raises FileNotFoundError if any kernel module or the spec cannot be
    read -- a kernel that cannot be measured cannot be qualified.
    """
    inputs = _packaged_inputs()
    entries = []
    for rel in KERNEL_MODULES:
        full = inputs.get(rel, REPO_ROOT / rel)
        if not full.is_file():
            raise FileNotFoundError(
                f"authority kernel module missing: {rel}. "
                "A kernel that cannot be measured cannot be qualified.")
        entries.append(f"{rel}:{_sha256_file(full, what='module')}")
    spec_file = Path(spec) if spec is not None else spec_path()
    spec_hash = _sha256_file(spec_file, what="spec")
    canonical = json.dumps(
        {"kernel_modules": sorted(entries), "spec_hash": spec_hash},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
