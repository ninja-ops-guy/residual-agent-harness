# Training: Developers (ENT7-R5, ENT7-R6)

Requirement: **ENT7-R5** — role-specific training for Developers (module
development, engine adapter development). Requirement: **ENT7-R6** —
hands-on exercises against a **sandboxed Residual instance** are mandatory.

Tracked via `residual/licensing/training.py` (`TrainingRecord`, role
`developer`). Required exercises: `build_module`, `write_engine_adapter`.

## Modules

1. **Contract-first development** (2h): `residual/core.py` contracts,
   `ContractError`, canonical JSON, hashing; why no model-generated code
   is executed.
2. **Module development** (3h): manifest, permissions, extension points
   (`residual/extensions.py`, `residual/modules`), validation and
   quarantine behavior, signing for the marketplace.
3. **Engine adapter development** (3h): adapter interface, verifier
   integration, emitting receipts, error taxonomy, brake-friendly failure
   modes.
4. **Testing** (1.5h): pytest conventions in `tests/`, writing verifier
   checks, receipt assertions.

## Hands-On Exercises (Sandbox Required, ENT7-R6)

| Exercise | ID | Task | Pass criteria |
|---|---|---|---|
| Build a module | `build_module` | Implement a module that adds a report-generation task type; pass all install validation gates in the sandbox | Module installs cleanly; smoke task receipts PASS; manifest permissions least-privilege |
| Write an engine adapter | `write_engine_adapter` | Adapt a mock engine; produce valid receipts; demonstrate a verifier FAIL path that trips a brake safely | Receipts verify; FAIL path quarantines correctly; adapter tests green |

## Assessment

Exercises run in the developer sandbox; completion recorded via
`TrainingRecord`. Graduates may submit modules for marketplace review
and adapters for production CAB review.
