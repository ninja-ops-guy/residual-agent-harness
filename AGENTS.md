# AGENTS.md — RESIDUAL agent entrypoint

This repository is verifier-first. Agents propose work; host-owned checks, evidence, governance, and integration decide what is accepted.

## Read this first

Before changing code or making a setup/status claim, read these in order:

1. `docs/wiki/AGENT-BOOTSTRAP.md` — deterministic setup and task routing.
2. `docs/CURRENT_STATUS.md` — current accepted/draft/unknown boundaries.
3. `docs/wiki/INTEGRATION-SKILLS.md` — reusable setup/integration workflows.
4. The task-specific canonical document from `docs/wiki/DOCS-MAP.md`.

For the shortest operator path, use `START-HERE.md`. For the core offline harness, use `docs/quickstart.md`.

## Authority order

When sources disagree, use this order:

1. Current source, tests, workflows, and retained exact-revision evidence.
2. `docs/CURRENT_STATUS.md` for repository-wide claim/status boundaries.
3. Normative specs for intended behavior.
4. Wiki pages as navigation and operating guidance.

The wiki is not a second status ledger.

## Non-negotiable boundaries

- Never convert `FAIL`, `UNKNOWN`, `BLOCKED`, skips, provider errors, or missing evidence into `PASS`.
- Never treat implementation presence, a draft PR, a scripted fixture, or a development scaffold as accepted capability or scientific evidence.
- Worker/model output is a candidate. It does not get acceptance authority.
- Preserve exact-revision evidence and first-failure history.
- Before touching Factory M2/M3/M4 trust-surface files, read `docs/status/FACTORY_OWNERSHIP_GATE.md`.
- A changed PR head requires fresh applicable qualification and a fresh exact-head maintainer attestation under `docs/governance/SOLO_MAINTAINER_POLICY.md`.
- Do not weaken checks, baselines, evidence bindings, protected-path rules, or verifier authority to make a change pass.

## Fast setup

Command Station:

```text
Windows: Start-Station.cmd
macOS:   Start-Station.command
Linux:   bash Start-Station.sh
UI:      http://localhost:8765
```

Native Station:

```bash
python3 -m residual.station.server --open
```

Offline core harness:

```bash
python3 -m residual run examples/onboarding/sample_project/task.json \
  --config examples/onboarding/config.toml --output runs/quickstart
bash examples/onboarding/demo.sh
```

## Task routing

- Setup / onboarding → `START-HERE.md`, `docs/quickstart.md`
- Providers / models → `docs/station/MODULAR-LAYERS.md`, `docs/extending.md`
- Command Station → `docs/station/`
- Factory M2/M3/M4 → `docs/factory/` plus ownership/status docs
- Studio → `docs/studio/`
- Swarm / multi-agent work → `docs/swarm/` plus Factory contracts
- Enterprise → `docs/enterprise/`
- Research / benchmarks → `docs/research.md`, `docs/evaluation.md`, `docs/controlled-evaluation.md`
- Security / release → `docs/security/`, `docs/release/`, `docs/governance/`, `docs/status/`

If an integration exists only on an open PR, keep it explicitly draft/unaccepted until its exact head satisfies the repository's applicable gates.
