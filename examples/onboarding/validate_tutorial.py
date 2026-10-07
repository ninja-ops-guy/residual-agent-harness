#!/usr/bin/env python3
"""Module-author tutorial validation (Track O).

Executes the steps in docs/module-tutorial.md against a generated example
module and asserts each documented invariant holds:

1. A module implements the documented ``StationModule`` surface: ``name``,
   ``version``, ``quarantine_policies()``, ``verifiers()``, ``brakes()``,
   ``on_run_opened(spec)``, ``on_run_closed(result)``.
2. Quarantine policies return ``None`` (allow) or a reason string (deny).
3. Verifiers return ``(CheckResult, reason)`` and declare a stable revision.
4. Brakes expose synchronous ``update(event)`` / ``reset()`` and return
   typed ``BrakeTrip`` values.
5. ``residual-module validate pkg:Class --source-root .`` reports the module
   valid.

Usage: python3 examples/onboarding/validate_tutorial.py
Exit 0 when every tutorial step validates; non-zero otherwise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

def _repo_root() -> Path:
    """Locate the checkout that provides the importable ``residual`` package."""
    for base in [Path(__file__).resolve().parents[2], *map(Path, sys.path),
                 *map(Path, os.environ.get("PYTHONPATH", "").split(os.pathsep))]:
        try:
            if (base / "residual" / "__init__.py").is_file():
                return base
        except (OSError, IndexError):
            continue
    raise SystemExit("tutorial validation FAILED: residual package not importable")


REPO_ROOT: Path  # resolved inside main()

MODULE_SOURCE = textwrap.dedent('''
    """Example StationModule written exactly as docs/module-tutorial.md prescribes."""
    import hashlib
    import json
    from residual.brakes import BrakeAction, BrakeTrip
    from residual.extensions import CheckType, VerifierDescriptor, VerifierRevision
    from residual.verifier import CheckResult

    def example_policy(action):
        return None if action.get("kind") == "read" else "writes require host approval"

    def example_evaluator(value, parameters):
        if value is None:
            return CheckResult.FAIL, "value must be present"
        return CheckResult.PASS, "value present"

    class ExampleBrake:
        name = "example_brake"
        def __init__(self):
            self.events = 0
        def update(self, event):
            self.events += 1
            tripped = self.events > 100
            obs = hashlib.sha256(json.dumps(event, sort_keys=True, default=str).encode()).hexdigest()
            return BrakeTrip(self.name, "event flood" if tripped else "within budget",
                             obs, BrakeAction.ABORT if tripped else BrakeAction.CONTINUE)
        def reset(self):
            self.events = 0

    class ExampleModule:
        name = "example"
        version = "1.0.0"
        def quarantine_policies(self):
            return (example_policy,)
        def verifiers(self):
            revision = VerifierRevision.from_artifact(__file__, configuration={}, policy={})
            return {"example_check": VerifierDescriptor(CheckType.MECHANICAL, example_evaluator, revision)}
        def brakes(self):
            return (ExampleBrake(),)
        def on_run_opened(self, spec):
            return None
        def on_run_closed(self, result):
            return None
''')


def fail(message: str) -> None:
    print(f"tutorial validation FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    global REPO_ROOT
    REPO_ROOT = _repo_root()
    tmp = Path(tempfile.mkdtemp(prefix="residual-tutorial-"))
    (tmp / "my_residual_module.py").write_text(MODULE_SOURCE)

    # Step 1: the module surface imports and instantiates.
    sys.path.insert(0, str(tmp))
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        from my_residual_module import ExampleModule  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"module import: {exc}")

    module = ExampleModule()
    for attr in ("name", "version", "quarantine_policies", "verifiers",
                 "brakes", "on_run_opened", "on_run_closed"):
        if not hasattr(module, attr):
            fail(f"module missing documented attribute {attr!r}")
    print("step 1 OK: StationModule surface present")

    # Step 2-4: protocol shapes behave as documented.
    from residual.brakes import BrakeTrip  # noqa: PLC0415
    from residual.verifier import CheckResult  # noqa: PLC0415

    policy = module.quarantine_policies()[0]
    decision = policy({"kind": "write"})
    if isinstance(decision, bool):
        fail("boolean quarantine decisions are forbidden by the tutorial")
    if not (decision is None or isinstance(decision, str)):
        fail("quarantine policy must return None or a reason string")

    verifiers = module.verifiers()
    if not isinstance(verifiers, dict) or not verifiers:
        fail("verifiers() must return a dict of named VerifierDescriptors")
    descriptor = next(iter(verifiers.values()))
    result = descriptor.evaluator("x", {})
    if not (isinstance(result, tuple) and len(result) == 2
            and isinstance(result[0], CheckResult) and isinstance(result[1], str)):
        fail("verifier evaluator must return (CheckResult, reason)")
    if not getattr(descriptor, "revision", None):
        fail("verifier must declare a stable revision")

    brake = module.brakes()[0]
    trip = brake.update({"event_type": "demo"})
    if not isinstance(trip, BrakeTrip):
        fail("brake update must return a typed BrakeTrip")
    brake.reset()
    print("steps 2-4 OK: quarantine / verifier / brake semantics validated")

    # Step 5: residual-module validate CLI accepts the module.
    env = dict(os.environ, PYTHONPATH=f"{REPO_ROOT}{os.pathsep}{tmp}")
    proc = subprocess.run(
        [sys.executable, "-m", "residual.marketplace.cli", "validate",
         "my_residual_module:ExampleModule", "--source-root", "."],
        capture_output=True, text=True, cwd=tmp, env=env,
    )
    if proc.returncode != 0:
        fail(f"residual-module validate exited {proc.returncode}: {proc.stderr.strip()}")
    report = json.loads(proc.stdout)
    if report.get("name") != "example" or report.get("verifiers") != 1 or report.get("brakes") != 1:
        fail(f"residual-module validate report unexpected: {report}")
    print("step 5 OK: residual-module validate accepted the module")
    print("tutorial validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
