# Agent Bootstrap

Use this page as the deterministic first-run playbook for a coding agent, operations agent, or integration agent.

## 0. Establish the revision and claim boundary

Before doing work:

```bash
git rev-parse HEAD
git status --short
```

Then read:

- `../CURRENT_STATUS.md` — accepted/draft/unknown repository status.
- `../../implementation-status.yaml` — implementation presence only; **not** qualification.
- `../governance/SOLO_MAINTAINER_POLICY.md` — merge authority.
- `../status/FACTORY_OWNERSHIP_GATE.md` before any protected Factory change.

Do not inherit a PASS from another commit, branch, environment, or predecessor run.

## 1. Classify the task

Choose exactly one primary lane before reading broadly:

| Lane | Read first | Typical work |
| --- | --- | --- |
| Operate Station | `../../START-HERE.md` | launch, model setup, missions, exports |
| Core harness | `../quickstart.md` + `../../HARNESS.md` | obligations, checks, receipts, CLI |
| Provider/model | `../station/MODULAR-LAYERS.md` | built-in providers, failover, observations |
| Custom extension | `../extending.md` | provider/check/solver/plugin/task |
| Factory | `../factory/PLAN-CONTRACT.md` | M2/M3/M4 execution/evidence/integration |
| Studio | `../studio/README.md` | platform/IDE direction |
| Enterprise | `../enterprise/README.md` | IAM, compliance, tenancy, HA/DR, integrations |
| Research | `../research.md` | experiments, claims, evidence |
| Release/security | `OPERATIONS.md` | qualification, governance, release review |

Use `DOCS-MAP.md` only after selecting the lane.

## 2. Bring up a runnable baseline

### Track A — Command Station with Docker

Requirements: Docker Desktop, or Docker Engine with Compose.

```bash
bash Start-Station.sh
```

Windows uses `Start-Station.cmd`. macOS can use `Start-Station.command`.

Open `http://localhost:8765` and run **Run training mission** before attaching an LLM. That path is scripted, makes no model call, and exercises the operator workflow.

For configured NVIDIA Container Toolkit hosts:

```bash
docker compose -f compose.yaml -f compose.nvidia.yaml up --build -d
```

### Track B — native Station

Requires Python 3.11+ and Git.

```bash
python3 -m residual.station.server --open
```

Windows:

```text
py -3 -m residual.station.server --open
```

### Track C — core offline harness

From a source checkout:

```bash
python3 -m residual run examples/onboarding/sample_project/task.json \
  --config examples/onboarding/config.toml --output runs/quickstart

bash examples/onboarding/demo.sh
```

The onboarding fixture is scripted/offline. It is a controller/evidence test, not live-model evidence.

## 3. Verify the baseline before editing

Core smoke:

```bash
python3 -m residual demo
python3 -m unittest discover -s tests -v
```

The repository contains narrower workflows and qualification gates for sensitive scopes. Do not assume a generic green unit suite replaces those gates.

Useful workflow families include:

- `ci.yml`
- `clean-install-qualification.yml`
- `control-plane.yml`
- `factory-execution.yml` / `factory.yml` / `factory-ownership.yml`
- `maintainer-approval.yml`
- `measured-eval-binding.yml`
- `pages.yml`
- `pr-agent.yml`
- `station.yml`
- WebVM/browser/runtime diagnostic workflows

Read `.github/workflows/` and the task-specific status docs before claiming exact-head qualification.

## 4. Load the minimum context needed

Agents should prefer a narrow context bundle over the entire repository.

### Provider task bundle

- `../station/MODULAR-LAYERS.md`
- `../../ai_providers/`
- `../extending.md`
- relevant provider tests
- `../CURRENT_STATUS.md`

### Factory task bundle

- `../factory/PLAN-CONTRACT.md`
- task-specific `../factory/*.md`
- `../status/FACTORY_OWNERSHIP_GATE.md`
- relevant `tests/test_factory_*`
- `../CURRENT_STATUS.md`

### Enterprise integration task bundle

- `../enterprise/README.md`
- `../enterprise/ENTERPRISE_SPECS.md`
- `../enterprise/TRACEABILITY.md`
- `../../residual/integrations/`
- relevant `tests/enterprise/`

### Research task bundle

- `../research.md`
- `../evaluation.md`
- `../controlled-evaluation.md`
- `../measured-eval-binding.md`
- the frozen workload/protocol for the experiment

## 5. Agent working contract

Before editing, state internally:

- exact base SHA;
- files/subsystems in scope;
- authority boundary that must remain host-owned;
- tests/evidence required;
- whether any path is protected;
- what would force a stop instead of a workaround.

During work:

- prefer the smallest fail-closed change;
- preserve immutable/evidence identities;
- bound I/O and retries;
- add negative-path tests for trust-boundary changes;
- do not silently broaden provider/tool/filesystem authority;
- do not “fix” CI by weakening the asserted property.

After work:

1. Run the narrowest deterministic tests first.
2. Run broader applicable tests.
3. Re-read the diff for authority/evidence changes.
4. Record remaining `UNKNOWN`/`BLOCKED` honestly.
5. Let exact-head CI and governance decide merge eligibility.

## 6. Stop conditions

Stop and report the boundary instead of improvising if:

- a protected path changed without an authorized baseline transition;
- the exact revision cannot be identified;
- required evidence is unavailable;
- a test is skipped because the host lacks a required capability;
- a provider error prevents semantic evaluation;
- a benchmark fixture would be mistaken for an external/official result;
- a change requires weakening verifier, receipt, isolation, or acceptance semantics;
- the PR head changed after approval/attestation.

## 7. Hand-off template

Use this compact hand-off for another agent:

```text
BASE: <exact SHA>
LANE: <station|core|provider|factory|studio|enterprise|research|release>
SCOPE: <paths>
CANONICAL DOCS: <paths>
PROTECTED BOUNDARY: <none or named gate>
TESTS RUN: <commands/results>
EVIDENCE: <artifact/run identifiers>
STATUS: PASS | FAIL | UNKNOWN | BLOCKED by claim
UNRESOLVED: <items>
NEXT SAFE ACTION: <one action>
```
