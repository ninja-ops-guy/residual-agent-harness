# Module development tutorial

A module implements `StationModule`: `name`, `version`, `quarantine_policies()`, `verifiers()`, `brakes()`, `on_run_opened(spec)`, and `on_run_closed(result)`. Registration remains host-selected and freezes before execution.

Quarantine policies return `None` to allow or a reason string to deny; boolean decisions are forbidden. Verifiers return `(CheckResult, reason)` and declare a stable revision. Brakes implement synchronous `update(event)` and `reset()` methods and return typed `BrakeTrip` values.

Package external modules with:

```toml
[project.entry-points."residual.modules"]
example = "my_residual_module:ExampleModule"
```

Validate before publication:

```bash
residual-module validate my_residual_module:ExampleModule --source-root .
```

Marketplace packages use detached Ed25519 signatures over the package SHA-256 plus public key. Installation is staged and published atomically only after signature and package checks pass.
