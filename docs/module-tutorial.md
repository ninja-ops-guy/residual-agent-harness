# Module development tutorial

A module implements the host-selected `StationModule` surface defined in `residual.extensions`: `name`, `version`, `quarantine_policies()`, `verifiers()`, `brakes()`, `on_run_opened(spec)`, and `on_run_closed(result)`. Registration is explicit and freezes before execution; modules are not discovered by scanning arbitrary directories at runtime.

`quarantine_policies()` returns a tuple of policy callables. Each policy returns `None` to allow an action or a non-empty reason string to deny it; boolean policy decisions are forbidden.

`verifiers()` returns a dictionary mapping stable verifier names to `VerifierDescriptor` objects. A descriptor binds a `CheckType`, evaluator, and stable `VerifierRevision`. Evaluators return `(CheckResult, reason)`; a worker's own success claim is not a verifier result.

`brakes()` returns fresh brake instances. Brakes expose synchronous `update(event)` and `reset()` methods, and `update()` returns a typed `BrakeTrip` containing the brake name, reason, observation digest, and `BrakeAction`.

A minimal module therefore looks like:

```python
from residual.extensions import CheckType, VerifierDescriptor, VerifierRevision
from residual.verifier import CheckResult

class ExampleModule:
    name = "example"
    version = "1.0.0"

    def quarantine_policies(self):
        def policy(action):
            return None if action.get("kind") == "read" else "writes require approval"
        return (policy,)

    def verifiers(self):
        def evaluator(value, parameters):
            if value is None:
                return CheckResult.FAIL, "value must be present"
            return CheckResult.PASS, "value present"

        revision = VerifierRevision.from_artifact(
            __file__, configuration={}, policy={}
        )
        return {
            "example_check": VerifierDescriptor(
                CheckType.MECHANICAL, evaluator, revision
            )
        }

    def brakes(self):
        return ()

    def on_run_opened(self, spec):
        return None

    def on_run_closed(self, result):
        return None
```

Package external modules with:

```toml
[project.entry-points."residual.modules"]
example = "my_residual_module:ExampleModule"
```

Validate the same protocol the host will consume before publication:

```bash
residual-module validate my_residual_module:ExampleModule --source-root .
```

The repository also includes an executable tutorial validator:

```bash
python examples/onboarding/validate_tutorial.py
```

Marketplace packages use detached Ed25519 signatures over the package digest and signing identity. Installation is staged and only published after signature, package, and module-contract validation succeed.
