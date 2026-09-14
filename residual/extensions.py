"""Explicit host-selected extensions, frozen when a controller is constructed."""
from __future__ import annotations

import inspect
import threading
import weakref
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Protocol

from .brakes import BrakeAction, BrakeTrip
from .core import ContractError, digest, identifier, strict_json, canonical
from .goalspec import CheckType
from .receipts import StationReceipt, ReceiptReference, cache_key, hash_id, verifier_id
from .verifier import CheckResult, Verifier


@dataclass(frozen=True)
class VerifierRevision:
    implementation_hash: str
    configuration_hash: str
    policy_hash: str
    proof_hash: str | None = None

    def __post_init__(self):
        for value in (self.implementation_hash, self.configuration_hash, self.policy_hash):
            hash_id(value)
        if self.proof_hash is not None:
            hash_id(self.proof_hash)

    @property
    def effective_revision(self) -> str:
        return digest({"schema": "residual.verifier.revision.v1", **vars(self)})

    @classmethod
    def from_artifact(cls, path: str | Path, *, configuration: dict, policy: dict,
                      proof_hash: str | None = None) -> VerifierRevision:
        """Host explicitly selects the implementation artifact and configuration."""
        import hashlib
        return cls(hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                   digest(configuration), digest(policy), proof_hash)


@dataclass(frozen=True)
class VerifierDescriptor:
    check_type: CheckType
    evaluator: Callable
    revision: VerifierRevision

    def __post_init__(self):
        if not isinstance(self.check_type, CheckType) or not isinstance(self.revision, VerifierRevision):
            raise ContractError("verifier requires a check type and revision identity")
        _signature(self.evaluator, 2)

    @property
    def effective_revision(self) -> str:
        return digest({"revision": self.revision.effective_revision, "check_type": self.check_type.value})


class StationModule(Protocol):
    name: str
    version: str
    def quarantine_policies(self) -> tuple: ...
    def verifiers(self) -> dict[str, VerifierDescriptor]: ...
    def brakes(self) -> tuple: ...
    def on_run_opened(self, spec) -> None: ...
    def on_run_closed(self, result) -> None: ...


def _signature(function, argc):
    if not callable(function) or inspect.iscoroutinefunction(function):
        raise ContractError("extension hook must be a synchronous callable")
    try:
        signature = inspect.signature(function)
        signature.bind(*([None] * argc))
    except (ValueError, TypeError):
        raise ContractError("invalid extension hook signature") from None
    return signature


class _GuardedBrake:
    def __init__(self, brake, name):
        self._brake, self.name = brake, name
        self._reset_failed = False

    def reset(self):
        self._reset_failed = False
        try:
            if self._brake.reset() is not None:
                self._reset_failed = True
        except Exception:
            self._reset_failed = True

    def update(self, event):
        try:
            if self._reset_failed:
                raise ValueError()
            # Each enforcement hook receives its own detached host event.
            trip = self._brake.update(strict_json(canonical(event)))
            if trip is None:
                return None
            if (not isinstance(trip, BrakeTrip) or not isinstance(trip.recommended_action, BrakeAction)
                    or not isinstance(trip.trip_reason, str) or not trip.trip_reason.strip()):
                raise ValueError()
            return BrakeTrip(self.name, trip.trip_reason[:1000], digest(event), trip.recommended_action)
        except Exception:
            return BrakeTrip(self.name, "extension_brake_failed", digest(event), BrakeAction.ABORT)


class StationExtensionRegistry:
    """Registration is atomic; hooks are never probed with invented actions.

    One registry has one active run (module lifecycle state is not shared across
    concurrent projects). Construct a separate registry per project/run factory.
    Registered Python code is trusted; freeze protects registration, not arbitrary
    mutation of Python objects by the host that owns them.
    """
    def __init__(self):
        self._modules = {}
        self._versions = {}
        self._verifiers = {}
        self._policies = ()
        self._frozen = False
        self._lock = threading.RLock()
        self._active = threading.Lock()
        self._issued_brakes = []
        self._diagnostics = []

    @property
    def frozen(self):
        return self._frozen

    @property
    def diagnostics(self):
        return tuple(dict(item) for item in self._diagnostics)

    @property
    def modules(self):
        return tuple(self._versions.items())

    def register_module(self, module: StationModule, *, revisions: dict[str, VerifierRevision] | None = None):
        with self._lock:
            if self._frozen:
                raise ContractError("extension registry is frozen")
            name = identifier(module.name)
            if name in self._modules or not isinstance(module.version, str) or not module.version.strip():
                raise ContractError("duplicate module or missing version")
            for hook in ("quarantine_policies", "verifiers", "brakes"):
                _signature(getattr(module, hook, None), 0)
            for hook in ("on_run_opened", "on_run_closed"):
                _signature(getattr(module, hook, None), 1)
            if hasattr(module, "on_event"):
                _signature(module.on_event, 2)
            policies, declarations = module.quarantine_policies(), module.verifiers()
            if not isinstance(policies, tuple) or not isinstance(declarations, dict):
                raise ContractError("module policies/verifiers have invalid container types")
            for policy in policies:
                annotation = _signature(policy, 1).return_annotation
                if annotation is bool or "bool" in str(annotation):
                    raise ContractError("boolean policy returns are forbidden")
            pending = {}
            for local, descriptor in declarations.items():
                identifier(local)  # local only; cannot shadow another namespace
                full = verifier_id(f"{name}:{local}")
                if isinstance(descriptor, tuple):
                    if len(descriptor) != 2 or not revisions or local not in revisions:
                        raise ContractError("legacy verifier requires explicit host revision identity")
                    descriptor = VerifierDescriptor(*descriptor, revisions[local])
                if not isinstance(descriptor, VerifierDescriptor):
                    raise ContractError("invalid verifier descriptor")
                pending[full] = descriptor
            if revisions and set(revisions) - set(declarations):
                raise ContractError("revision provided for an unknown verifier")
            # Validate factories structurally now. Instances are created per run.
            self._modules[name] = (module, tuple(policies))
            self._versions[name] = module.version
            self._policies += tuple(policies)
            self._verifiers.update(pending)
        return self

    def freeze(self):
        with self._lock:
            self._frozen = True
        return self

    def policies(self):
        return self._policies

    def verifiers(self):
        return MappingProxyType(dict(self._verifiers))

    def compose(self, base: Verifier, spec) -> Verifier:
        evaluators = dict(base.evaluators)
        for name, desc in self._verifiers.items():
            if name in evaluators:
                raise ContractError("extension evaluator shadows a host evaluator")
            evaluators[name] = desc.evaluator
        for criterion in spec.success_criteria:
            desc = self._verifiers.get(criterion.evaluator)
            if desc and desc.check_type != criterion.check_type:
                raise ContractError("criterion check type differs from registered verifier")
        return Verifier(evaluators)

    def register_checks(self, registry):
        """Explicit adapter to the obligation harness; no automatic plugin imports."""
        from .core import Verdict
        if set(self._verifiers) & set(registry.checks):
            raise ContractError("extension check shadows a host check")
        for name, descriptor in self._verifiers.items():
            def check(value, context, descriptor=descriptor):
                result, reason = descriptor.evaluator(value, context.obligation.parameters)
                if not isinstance(result, CheckResult) or result == CheckResult.SKIPPED or not isinstance(reason, str):
                    return Verdict("unknown", "invalid_extension_result")
                return Verdict(result.value, "extension_" + result.value, reason[:1000])
            registry.check(name, check, descriptor.effective_revision, identity=descriptor.revision,
                           check_type=descriptor.check_type.value)

    def brakes(self):
        with self._lock:
            raw, guarded, names = [], [], set()
            for domain, (module, _) in self._modules.items():
                instances = module.brakes()
                if not isinstance(instances, tuple):
                    raise ContractError("module brakes must return a tuple of fresh instances")
                for brake in instances:
                    local = identifier(brake.name)
                    name = f"{domain}:{local}"
                    self._issued_brakes = [ref for ref in self._issued_brakes if ref() is not None]
                    if name in names or any(brake is old for old in raw) or any(ref() is brake for ref in self._issued_brakes):
                        raise ContractError("duplicate or reused extension brake")
                    _signature(brake.update, 1)
                    _signature(brake.reset, 0)
                    names.add(name)
                    raw.append(brake)
                    guarded.append(_GuardedBrake(brake, name))
            for brake in raw:
                try:
                    self._issued_brakes.append(weakref.ref(brake))
                except TypeError:
                    # A slotted host brake without weakref support stays retained
                    # so it cannot be recycled into a concurrent/future run.
                    self._issued_brakes.append(lambda brake=brake: brake)
            return tuple(guarded)

    def acquire(self):
        if not self._frozen:
            raise ContractError("registry must be frozen at controller construction")
        if not self._active.acquire(blocking=False):
            raise ContractError("extension registry already has an active run")

    def release(self):
        self._active.release()

    def _diagnostic(self, name, hook):
        self._diagnostics.append({"module": name, "hook": hook, "code": "extension_hook_failed"})

    def on_run_opened(self, spec):
        failures = []
        for name, (module, _) in self._modules.items():
            try:
                if module.on_run_opened(spec) is not None:
                    raise ValueError()
            except Exception:
                self._diagnostic(name, "on_run_opened")
                failures.append(name)
        return tuple(failures)

    def on_run_closed(self, result):
        for name, (module, _) in self._modules.items():
            try:
                if module.on_run_closed(result) is not None:
                    raise ValueError()
            except Exception:
                self._diagnostic(name, "on_run_closed")

    def observe(self, kind, payload):
        for name, (module, _) in self._modules.items():
            observer = getattr(module, "on_event", None)
            if observer:
                try:
                    observer(kind, strict_json(canonical(payload)))
                except Exception:
                    self._diagnostic(name, "on_event")
