# RESIDUAL Wiki

This is the agent-first navigation layer for the RESIDUAL documentation set. It is designed so a human operator or coding agent can go from a fresh checkout to the correct setup, integration, validation, or research path without reading the repository linearly.

> **Source-of-truth rule:** this wiki routes to canonical documents; it does not replace them. For current acceptance/qualification boundaries, always read `../CURRENT_STATUS.md`.

## Start here by intent

| I need to… | Open first | Then |
| --- | --- | --- |
| Run Command Station | `../../START-HERE.md` | `AGENT-BOOTSTRAP.md` |
| Run the core harness | `../quickstart.md` | `../../HARNESS.md` |
| Give an agent enough context to work safely | `../../AGENTS.md` | `AGENT-BOOTSTRAP.md` |
| Add/configure an LLM provider | `../station/MODULAR-LAYERS.md` | `INTEGRATION-SKILLS.md` |
| Add a custom provider/check/solver | `../extending.md` | `INTEGRATION-SKILLS.md` |
| Work on Factory M2/M3/M4 | `../factory/PLAN-CONTRACT.md` | `../status/FACTORY_OWNERSHIP_GATE.md` |
| Work on Studio | `../studio/README.md` | `../studio/STUDIO_SPECS.md` |
| Connect enterprise systems | `../enterprise/README.md` | `INTEGRATION-SKILLS.md` |
| Operate/release safely | `OPERATIONS.md` | `../governance/SOLO_MAINTAINER_POLICY.md` |
| Run an experiment | `../research.md` | `../evaluation.md` + `../controlled-evaluation.md` |
| Find any document | `DOCS-MAP.md` | canonical source |

## Wiki pages

- **`AGENT-BOOTSTRAP.md`** — deterministic onboarding, environment selection, reading order, verification, and stop conditions.
- **`INTEGRATION-SKILLS.md`** — reusable skill cards for provider, enterprise, swarm, research, and release work.
- **`OPERATIONS.md`** — run, qualify, troubleshoot, and merge without crossing authority boundaries.
- **`DOCS-MAP.md`** — comprehensive index of the documentation tree and root documentation.

## Two supported onboarding tracks

### Operator / Command Station

1. Install Docker Desktop/Engine, or choose native mode.
2. Launch with the platform script for the host OS.
3. Open `http://localhost:8765`.
4. Run the training mission before attaching a model.
5. Configure local/cloud providers in Model Workshop.
6. Run a real project only after reviewing project command-check permissions and cloud eligibility.

Canonical instructions: `../../START-HERE.md`.

### Developer / core harness

1. Use Python 3.11+ and Git.
2. From the repository root, run the scripted onboarding fixture.
3. Verify the resulting evidence trace.
4. Read the architecture and extension docs before adding providers, checks, solvers, or execution paths.

Canonical instructions: `../quickstart.md` and `../../HARNESS.md`.

## Mental model

```text
Goal / mission
    ↓
Host-owned obligations / contracts
    ↓
Worker or model proposes candidate work
    ↓
Independent host-owned verification
    ├─ PASS → receipt/evidence → deterministic integration
    └─ FAIL / UNKNOWN → bounded residual / retry / escalation
```

The project can expose many interfaces—Station, Factory, Studio, WebVM, providers, enterprise integrations, swarm runtimes—but they all inherit the same basic authority rule: **the worker proposes; the verifier/integrator decides**.

## Status discipline for agents

Before saying something is “supported”, “production ready”, “qualified”, “official”, or “proven”:

1. Read `../CURRENT_STATUS.md`.
2. Check whether the evidence applies to the exact revision/environment being discussed.
3. Separate **implemented**, **demonstrated**, **hypothesized**, and **established**.
4. Treat open/draft PRs as unaccepted unless the status document explicitly says otherwise.
5. Do not use local benchmark scaffolds as external leaderboard/official-program evidence.

## Documentation maintenance

When adding a substantial subsystem or onboarding path:

1. Add/update the canonical subsystem document.
2. Add it to `DOCS-MAP.md`.
3. Add a route here only if newcomers or agents need to find it quickly.
4. Do not copy rapidly changing status claims into multiple wiki pages.
