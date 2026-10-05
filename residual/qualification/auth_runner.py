"""Attack-manifest qualification runner (Track B2 implementation).

Turns the AUTH invariant specification's qualification from prose into an
executable, receipt-producing pipeline:

    manifest (data) -> runner -> attack execution -> receipt (evidence)

The runner answers one question per attack: *was this coercion rejected
for the reason the invariant names, against the exact candidate the
manifest names?* A "yes" is a PASS; anything else — including a denial
for an unknown reason — is a FAIL.

Normative basis: AUTH_INVARIANTS.md; design:
workspace/auth-invariant-family/MANIFEST_RUNNER_DESIGN.md.

New files only (Track B2). Track A owns emission
(residual/authority.py) and the kernel interface
(residual/authority_kernel.py); this module consumes them through lazy
imports and fails informatively in their absence.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable

from residual.core import canonical

# ---------------------------------------------------------------- constants

MANIFEST_SCHEMA = "residual.auth.manifest.v1"
RECEIPT_SCHEMA = "residual.auth.receipt.v1"

# Spec-fixed vocabulary (AUTH_INVARIANTS.md). Duplicated here (rather than
# imported from residual.authority) so the runner is self-contained and
# testable before/after Track A lands; the values are normative, not
# implementation-defined.
FAILURE_CODES = (
    "AMBIGUOUS_ACCEPTANCE_CONDITION",
    "UNBOUND_EVIDENCE_SOURCE",
    "UNRESOLVED_AUTHORITY",
    "UNPROVEN_ACCEPTANCE",
    "STALE_CONTRACT",
    "UNAUTHORIZED_CONTRACT_REINTERPRETATION",
    "UNAPPROVED_ACTION",
    "IMPLICIT_AUTHORITY_COERCION",
)
FAIL_CLOSED_STATES = (
    "NO_AUTHORITY_CHANGE",
    "NO_EXECUTION",
    "NO_IMPLICIT_DEFAULT",
    "NO_PROMOTION",
    "STALE_CONTRACT",
    "UNPROVEN",
)
INVARIANT_IDS = (
    "INV-AUTH-EVD-001",
    "INV-AUTH-IDN-002",
    "INV-AUTH-ACC-003",
    "INV-AUTH-CTR-004",
    "INV-AUTH-AMB-005",
    "INV-AUTH-AUT-006",
)
# Fixed pipeline precedence: the earliest-triggered invariant in this order
# is the primary code for a compound attack.
PRECEDENCE = (
    "INV-AUTH-AMB-005",
    "INV-AUTH-CTR-004",
    "INV-AUTH-IDN-002",
    "INV-AUTH-AUT-006",
    "INV-AUTH-EVD-001",
    "INV-AUTH-ACC-003",
)
CODE_TO_INVARIANT = {
    "AMBIGUOUS_ACCEPTANCE_CONDITION": "INV-AUTH-AMB-005",
    "UNAUTHORIZED_CONTRACT_REINTERPRETATION": "INV-AUTH-CTR-004",
    "STALE_CONTRACT": "INV-AUTH-CTR-004",
    "UNRESOLVED_AUTHORITY": "INV-AUTH-IDN-002",
    "UNAPPROVED_ACTION": "INV-AUTH-AUT-006",
    "UNBOUND_EVIDENCE_SOURCE": "INV-AUTH-EVD-001",
    "UNPROVEN_ACCEPTANCE": "INV-AUTH-ACC-003",
    "IMPLICIT_AUTHORITY_COERCION": "INV-AUTH-000",
}
SOURCE_TARGET = {
    "INV-AUTH-EVD-001": ("OBSERVATION", "EVIDENCE"),
    "INV-AUTH-IDN-002": ("IDENTITY", "AUTHORITY"),
    "INV-AUTH-ACC-003": ("TEST_RESULT", "ACCEPTANCE"),
    "INV-AUTH-CTR-004": ("INTERPRETATION", "CONTRACT"),
    "INV-AUTH-AMB-005": ("AMBIGUOUS_INTENT", "EXECUTABLE_AUTHORITY"),
    "INV-AUTH-AUT-006": ("SUGGESTION", "AUTHORIZATION"),
}

DEFAULT_TIMEOUT_S = 300

_ATTACK_ID_RE = re.compile(r"^AUTH-[A-Z0-9-]+-[NP][0-9]{2}$")
_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# ---------------------------------------------------------------- manifests


@dataclass(frozen=True)
class AttackManifest:
    schema: str
    attack_id: str
    invariant_id: str
    kind: str  # "negative" | "positive" | "compound"
    target_head: str
    target_tree: str
    target_contract_id: str
    attack_input: dict
    attack_input_hash: str
    expected_fail_closed_state: str | None
    expected_failure_code: str | None
    expected_triggered_codes: tuple = ()
    expected_success_artifact: dict | None = None
    description: str = ""
    timeout_s: int = DEFAULT_TIMEOUT_S


def _fail(path: Path, msg: str) -> ValueError:
    return ValueError(f"{path}: invalid manifest — {msg}")


def load_manifest(path: Path, *, default_timeout_s: int = DEFAULT_TIMEOUT_S) -> AttackManifest:
    """Load and validate one manifest. Refuses on schema or hash mismatch."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise _fail(path, f"unreadable JSON: {e}") from e
    if not isinstance(raw, dict):
        raise _fail(path, "top-level value must be an object")

    def req(name: str) -> Any:
        if name not in raw:
            raise _fail(path, f"missing required field {name!r}")
        return raw[name]

    schema = req("schema")
    if schema != MANIFEST_SCHEMA:
        raise _fail(path, f"unknown schema {schema!r}")
    attack_id = req("attack_id")
    if not isinstance(attack_id, str) or not _ATTACK_ID_RE.match(attack_id):
        raise _fail(path, f"attack_id {attack_id!r} does not match AUTH-<S>-<NNN>-<K><nn>")
    invariant_id = req("invariant_id")
    if invariant_id not in INVARIANT_IDS:
        raise _fail(path, f"unknown invariant_id {invariant_id!r}")
    kind = req("kind")
    if kind not in ("negative", "positive", "compound"):
        raise _fail(path, f"unknown kind {kind!r}")
    for name, pattern in (("target_head", _HEX40_RE), ("target_tree", _HEX40_RE),
                          ("target_contract_id", _HEX64_RE)):
        value = req(name)
        if not isinstance(value, str) or not pattern.match(value):
            raise _fail(path, f"{name} must be lowercase hex of the required length")
    attack_input = req("attack_input")
    if not isinstance(attack_input, dict):
        raise _fail(path, "attack_input must be an object")
    attack_input_hash = req("attack_input_hash")
    if not isinstance(attack_input_hash, str) or not _HEX64_RE.match(attack_input_hash):
        raise _fail(path, "attack_input_hash must be 64-char lowercase hex")
    recomputed = hashlib.sha256(canonical(attack_input).encode("utf-8")).hexdigest()
    if recomputed != attack_input_hash:
        raise _fail(path, "attack_input_hash mismatch — manifest tampered or stale")

    timeout_s = raw.get("timeout_s", default_timeout_s)
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, int) or timeout_s < 1:
        raise _fail(path, "timeout_s must be an integer >= 1")

    expected_triggered_codes = raw.get("expected_triggered_codes", [])
    if not isinstance(expected_triggered_codes, list) or not all(
            isinstance(c, str) and c in FAILURE_CODES for c in expected_triggered_codes):
        raise _fail(path, "expected_triggered_codes must be a list of known failure codes")

    description = raw.get("description", "")
    if not isinstance(description, str):
        raise _fail(path, "description must be a string")

    expected_failure_code = raw.get("expected_failure_code")
    expected_fail_closed_state = raw.get("expected_fail_closed_state")
    expected_success_artifact = raw.get("expected_success_artifact")

    if kind == "positive":
        if expected_failure_code is not None:
            raise _fail(path, "positive manifests must not name a failure code")
        if expected_fail_closed_state is not None:
            raise _fail(path, "positive manifests must not name a fail-closed state")
        if not isinstance(expected_success_artifact, dict):
            raise _fail(path, "positive manifests require expected_success_artifact object")
    else:  # negative | compound
        if expected_failure_code not in FAILURE_CODES:
            raise _fail(path, "negative/compound manifests require a known expected_failure_code")
        if expected_fail_closed_state not in FAIL_CLOSED_STATES:
            raise _fail(path, "negative/compound manifests require a known expected_fail_closed_state")
        if expected_success_artifact is not None:
            raise _fail(path, "negative/compound manifests must not carry expected_success_artifact")
        if kind == "compound" and not expected_triggered_codes:
            raise _fail(path, "compound manifests require non-empty expected_triggered_codes")

    return AttackManifest(
        schema=schema,
        attack_id=attack_id,
        invariant_id=invariant_id,
        kind=kind,
        target_head=raw["target_head"],
        target_tree=raw["target_tree"],
        target_contract_id=raw["target_contract_id"],
        attack_input=attack_input,
        attack_input_hash=attack_input_hash,
        expected_fail_closed_state=expected_fail_closed_state,
        expected_failure_code=expected_failure_code,
        expected_triggered_codes=tuple(expected_triggered_codes),
        expected_success_artifact=expected_success_artifact,
        description=description,
        timeout_s=timeout_s,
    )


# ---------------------------------------------------------------- identity


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def capture_candidate(root: Path | str = ".") -> tuple[str, str, bool]:
    """Return (head, tree, dirty) for the repo at root.

    Raises RuntimeError if the candidate identity cannot be established.
    """
    root = Path(root)
    head = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    dirty_raw = _git(root, "status", "--porcelain", "--untracked-files=no")
    if not head or not tree or dirty_raw is None:
        raise RuntimeError(f"cannot establish candidate identity for {root}")
    if not _HEX40_RE.match(head) or not _HEX40_RE.match(tree):
        raise RuntimeError(f"non-hex candidate identity for {root}")
    return head, tree, bool(dirty_raw)


def kernel_revision() -> str | None:
    """Track A (A3) interface: deterministic 64-hex authority-kernel identity.

    Returns None when the interface is absent — the runner binds null and
    fails the run closed (every receipt FAILs; see _execute_run).
    """
    try:
        from residual.authority_kernel import revision  # Track A (A3)
    except ImportError:
        return None
    value = revision()
    if not isinstance(value, str) or not _HEX64_RE.match(value):
        raise ValueError(f"authority_kernel.revision() returned invalid value: {value!r}")
    return value


# ---------------------------------------------------------------- outcomes


@dataclass(frozen=True)
class Rejected:
    """A typed Track A rejection: the coercion was blocked for a named reason."""
    code: str
    triggered_codes: tuple
    fail_closed_state: str


@dataclass(frozen=True)
class UncodedRejection:
    """A rejection without a typed failure code: denial for an unknown reason."""
    info: str  # exception type/message (truncated), or "timeout"


@dataclass(frozen=True)
class Succeeded:
    """The attack callable returned normally (no rejection observed)."""
    artifact: dict


def _typed_rejection_types() -> tuple:
    """Lazy import of Track A's AuthorityCoercionRejected.

    Pre-Track-A the import fails and every rejection is honestly uncoded;
    nothing here may define a competing type.
    """
    try:
        from residual.authority import AuthorityCoercionRejected  # Track A (A2)
        return (AuthorityCoercionRejected,)
    except ImportError:
        return ()


def execute(fn: Callable[[dict], dict], attack_input: dict,
           timeout_s: int) -> Rejected | UncodedRejection | Succeeded:
    """Execute one attack callable exactly once. No retries: flakiness is a FAIL."""
    _typed = _typed_rejection_types()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn, attack_input)
        try:
            artifact = future.result(timeout=timeout_s)
        except _typed as e:
            return Rejected(code=e.code,
                            triggered_codes=tuple(e.triggered_codes),
                            fail_closed_state=e.fail_closed_state)
        except FuturesTimeoutError:
            return UncodedRejection(info="timeout")
        except Exception as e:  # noqa: BLE001 - any uncoded outcome is evidence
            return UncodedRejection(info=f"{type(e).__name__}: {str(e)[:200]}")
    return Succeeded(artifact=artifact if isinstance(artifact, dict) else {})


# ---------------------------------------------------------------- decision


def _primary(triggered: tuple) -> str:
    """Derive the primary code from a triggered set via pipeline precedence.

    Recording order (lexicographic on invariant ID) and primary derivation
    (pipeline precedence) are distinct orderings; neither substitutes for
    the other.
    """
    order = {inv: i for i, inv in enumerate(PRECEDENCE)}
    best: str | None = None
    best_rank = len(PRECEDENCE)
    for code in triggered:
        inv = CODE_TO_INVARIANT.get(code)
        if inv is None or inv == "INV-AUTH-000":
            raise ValueError(f"unknown or generic code in triggered set: {code!r}")
        if order[inv] < best_rank:
            best, best_rank = code, order[inv]
    if best is None:
        raise ValueError("empty triggered set")
    return best


def decide(m: AttackManifest, outcome: Rejected | UncodedRejection | Succeeded,
           ) -> tuple[str, tuple]:
    """Decision procedure. Returns (result, notes) with result PASS|FAIL."""
    if m.kind == "positive":
        if not isinstance(outcome, Succeeded):
            info = getattr(outcome, "info", "")
            return "FAIL", (f"legal conversion rejected ({info}); "
                             "a system that rejects everything fails qualification",)
        notes = []
        for key, expected in (m.expected_success_artifact or {}).items():
            if outcome.artifact.get(key) != expected:
                notes.append(f"success artifact mismatch at {key!r}: "
                             f"expected {expected!r}, observed {outcome.artifact.get(key)!r}")
        return ("PASS" if not notes else "FAIL"), tuple(notes)

    # negative / compound
    if isinstance(outcome, Succeeded):
        return "FAIL", ("attack was not rejected; coercion succeeded",)
    if isinstance(outcome, UncodedRejection):
        return "FAIL", (f"rejected without a typed failure code "
                         f"(observed: {outcome.info}); denial for an unknown "
                         f"reason is not a pass",)
    try:
        primary = _primary(outcome.triggered_codes)
    except ValueError as e:
        return "FAIL", (str(e),)
    notes = []
    if primary != m.expected_failure_code:
        notes.append(f"expected {m.expected_failure_code}, observed primary {primary}")
    if outcome.fail_closed_state != m.expected_fail_closed_state:
        notes.append(f"expected state {m.expected_fail_closed_state}, "
                     f"observed {outcome.fail_closed_state}")
    if m.kind == "compound" and m.expected_triggered_codes:
        if set(outcome.triggered_codes) != set(m.expected_triggered_codes):
            notes.append("triggered set mismatch: silent or extra triggers "
                         f"(expected {sorted(m.expected_triggered_codes)}, "
                         f"observed {sorted(outcome.triggered_codes)})")
    return ("PASS" if not notes else "FAIL"), tuple(notes)


# ---------------------------------------------------------------- receipts

@dataclass(frozen=True)
class AuthQualificationReceipt:
    schema: str
    invariant_id: str
    attack_id: str
    kind: str  # "negative" | "positive" | "compound"
    result: str  # "PASS" | "FAIL"
    candidate_head: str
    candidate_tree: str
    contract_id: str
    kernel_revision: str | None  # None only if Track A interface absent
    source_type: str
    target_type: str
    expected_failure_code: str | None
    observed_failure_code: str | None  # primary observed code; null if uncoded
    observed_failure_codes: tuple = ()  # all triggered, invariant-ID order
    expected_fail_closed_state: str | None = None
    observed_fail_closed_state: str | None = None
    notes: tuple = ()
    evidence_receipt_hash: str = ""  # computed by sealed()

    def payload(self) -> dict:
        d = asdict(self)
        d.pop("evidence_receipt_hash")
        d["observed_failure_codes"] = list(self.observed_failure_codes)
        d["notes"] = list(self.notes)
        return d

    def sealed(self) -> "AuthQualificationReceipt":
        h = hashlib.sha256(
            (self.schema + "\n" + canonical(self.payload())).encode("utf-8")
        ).hexdigest()
        return replace(self, evidence_receipt_hash=h)

    def verify(self) -> bool:
        """Recompute the domain hash; False means the receipt was altered."""
        if not self.evidence_receipt_hash:
            return False
        return self.sealed().evidence_receipt_hash == self.evidence_receipt_hash


# ---------------------------------------------------------------- main loop

def _load_registry(registry: dict | None) -> dict:
    if registry is not None:
        return registry
    from tests.qualification.auth_attacks import ATTACKS  # Track C registry
    return ATTACKS


def _execute_run(manifests: list[AttackManifest], *, contract_id: str,
                 out_dir: Path, root: Path,
                 registry: dict | None) -> tuple[dict, list[AuthQualificationReceipt]]:
    head, tree, dirty = capture_candidate(root)
    for m in manifests:
        if m.target_head != head or m.target_tree != tree:
            raise RuntimeError(
                f"{m.attack_id}: manifest not pinned to this candidate "
                f"({head[:8]}/{tree[:8]}) — refusing")
        if m.target_contract_id != contract_id:
            raise RuntimeError(
                f"{m.attack_id}: manifest not pinned to contract "
                f"{contract_id[:8]} — refusing")
    if dirty:
        raise RuntimeError("working tree not clean — refusing to qualify")
    krev = kernel_revision()

    attacks = _load_registry(registry)
    receipts: list[AuthQualificationReceipt] = []
    receipts_dir = out_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    for m in manifests:
        if m.attack_id not in attacks:
            raise RuntimeError(f"{m.attack_id}: no registry entry — refusing to skip")
        entry = attacks[m.attack_id]
        entry_kind = entry.kind if hasattr(entry, "kind") else entry.get("kind")
        entry_fn = entry.fn if hasattr(entry, "fn") else entry.get("fn")
        if entry_kind != m.kind:
            raise RuntimeError(f"{m.attack_id}: registry/manifest kind mismatch "
                               f"({entry_kind!r} vs {m.kind!r}) — refusing")
        outcome = execute(entry_fn, m.attack_input, m.timeout_s)
        result, notes = decide(m, outcome)
        if krev is None:
            # Revised §7.1: a null kernel_revision fails every receipt closed,
            # with the receipt layer consistent with the aggregate layer.
            result = "FAIL"
            notes = notes + ("kernel_revision unbound — Track A3 not delivered",)
        source_type, target_type = SOURCE_TARGET[m.invariant_id]
        observed = outcome if isinstance(outcome, Rejected) else None
        receipt = AuthQualificationReceipt(
            schema=RECEIPT_SCHEMA,
            invariant_id=m.invariant_id,
            attack_id=m.attack_id,
            kind=m.kind,
            result=result,
            candidate_head=head,
            candidate_tree=tree,
            contract_id=contract_id,
            kernel_revision=krev,
            source_type=source_type,
            target_type=target_type,
            expected_failure_code=m.expected_failure_code,
            observed_failure_code=(observed.code if observed else None),
            observed_failure_codes=(tuple(sorted(
                observed.triggered_codes,
                key=lambda c: CODE_TO_INVARIANT[c])) if observed else ()),
            expected_fail_closed_state=m.expected_fail_closed_state,
            observed_fail_closed_state=(observed.fail_closed_state if observed else None),
            notes=notes,
        ).sealed()
        (receipts_dir / f"{m.attack_id}.json").write_text(
            json.dumps(receipt.payload()
                       | {"evidence_receipt_hash": receipt.evidence_receipt_hash},
                       indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        receipts.append(receipt)

    overall = ("PASS" if all(r.result == "PASS" for r in receipts)
               and krev is not None else "FAIL")
    run_manifest = {
        "schema": "residual.auth.run_manifest.v1",
        "candidate_head": head,
        "candidate_tree": tree,
        "contract_id": contract_id,
        "kernel_revision": krev,
        "result": overall,
        "derived_inv_auth_000": "PASS" if overall == "PASS" else "FAIL",
        "receipts": [r.attack_id for r in receipts],
        "results": {r.attack_id: r.result for r in receipts},
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run_manifest, receipts


def run(manifest_dir: Path | str, *, contract_id: str, out_dir: Path | str,
        root: Path | str = ".", registry: dict | None = None,
        timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    """Run every manifest in manifest_dir. Returns the run manifest dict.

    Refuses (raises) on: no manifests, candidate-identity mismatch, dirty
    tree, contract mismatch, missing registry entry, kind mismatch.
    """
    manifest_dir = Path(manifest_dir)
    manifests = [load_manifest(p, default_timeout_s=timeout_s)
                 for p in sorted(manifest_dir.glob("*.json"))]
    if not manifests:
        raise ValueError(f"no manifests in {manifest_dir}")
    run_manifest, _receipts = _execute_run(
        manifests, contract_id=contract_id, out_dir=Path(out_dir),
        root=Path(root), registry=registry)
    return run_manifest


def run_single_manifest(manifest_path: Path | str, *, contract_id: str,
                        root: Path | str = ".", out_dir: Path | str,
                        registry: dict | None = None,
                        timeout_s: int = DEFAULT_TIMEOUT_S) -> AuthQualificationReceipt:
    """Run one manifest; return its receipt. (Pytest-wrapper entry point.)"""
    m = load_manifest(Path(manifest_path), default_timeout_s=timeout_s)
    _run_manifest, receipts = _execute_run(
        [m], contract_id=contract_id, out_dir=Path(out_dir),
        root=Path(root), registry=registry)
    return receipts[0]


def release_report(run_manifest: dict) -> str:
    lines = [
        f"AUTH Qualification: "
        f"{sum(1 for r in run_manifest['results'].values() if r == 'PASS')}"
        f"/{len(run_manifest['results'])} child invariants PASS",
        f"INV-AUTH-000: {run_manifest['derived_inv_auth_000']} (derived)",
        f"Candidate: {run_manifest['candidate_head'][:12]}/{run_manifest['candidate_tree'][:12]}",
        f"Contract: {run_manifest['contract_id'][:16]}…",
        f"Kernel: {(run_manifest['kernel_revision'] or 'UNBOUND')[:16]}…",
        "Each result backed by an adversarial-test receipt.",
    ]
    return "\n".join(lines)
