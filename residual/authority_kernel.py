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
import os
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

#: Environment variable overriding the normative spec location.
SPEC_ENV_VAR = "RESIDUAL_AUTH_SPEC"

#: Spec filename; resolved against the workspace layout, never invented.
SPEC_FILENAME = "AUTH_INVARIANTS.md"


def spec_path() -> Path:
    """Locate the normative AUTH_INVARIANTS.md. Raises if unresolvable."""
    override = os.environ.get(SPEC_ENV_VAR)
    if override:
        path = Path(override)
        if path.is_file():
            return path
        raise FileNotFoundError(
            f"{SPEC_ENV_VAR} points at an unreadable spec: {override}")
    candidates = (
        REPO_ROOT.parent / "auth-invariant-family" / SPEC_FILENAME,
        Path.home() / "workspace" / "auth-invariant-family" / SPEC_FILENAME,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"normative spec {SPEC_FILENAME} not found; set {SPEC_ENV_VAR}. "
        "A kernel that cannot be measured against its spec cannot be qualified.")


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
    entries = []
    for rel in KERNEL_MODULES:
        full = REPO_ROOT / rel
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
