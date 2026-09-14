# Runbook: Module Installation — Validation and Rollback (ENT7-R4)

Requirement: **ENT7-R4** — runbook template for the "module installation"
operational scenario.

## Overview

Modules extend Residual and are treated as untrusted supply-chain
artifacts until validated. This runbook covers validation, installation,
and rollback.

## Pre-Installation

1. **Source check**: module from the marketplace or a signed internal
   build; unsigned modules are rejected in production.
2. **Change ticket**: CAB approval for production installations.
3. **Staging first**: install in the sandbox/staging station before
   production.
4. Snapshot current station configuration and module list (rollback
   baseline).

## Validation Gate

1. Signature verification and publisher identity check.
2. Static validation: manifest schema, declared permissions, contract
   declarations.
3. Sandbox execution: module runs in the sandboxed station with brakes
   armed; all outputs verified.
4. Security scan (per SPEC-ENT-005): dependency and SAST scan of module
   code; clean or triaged results required.
5. Smoke tasks: run the module's reference tasks; all receipts PASS.

Any gate failure → abort, quarantine the module artifact, and record the
failure.

## Installation

1. `residual modules install <artifact> --station <id>` (install is
   receipted).
2. Enable with least-privilege permissions only.
3. Monitor for 60 minutes: verifier verdict rate, brake state, error
   rates on tasks using the module.

## Rollback

Trigger rollback on: any contract violation attributable to the module,
brake trip, or smoke-task failure within the monitoring window.

1. Disable the module immediately: `residual modules disable <name>`.
2. Quarantine module outputs produced since installation; block dependent
   tasks.
3. `residual modules uninstall <name>` and restore the pre-install
   configuration snapshot.
4. Verify receipt chain integrity across the install window.
5. Post-mortem per the contract-violation runbook if violations occurred.

## Records

Installation, validation results, and any rollback are receipted and
referenced in the change ticket — auditors review these during compliance
reporting (auditor curriculum, ENT7-R5).
