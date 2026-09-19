# Operations and Release Playbook

This page connects the setup docs to the repository's qualification/governance model.

## Daily operating paths

### Start Station

Docker/platform launchers:

```text
Windows: Start-Station.cmd
macOS:   Start-Station.command
Linux:   bash Start-Station.sh
```

Native:

```bash
python3 -m residual.station.server --open
```

Default UI: `http://localhost:8765`.

### Run the offline onboarding fixture

```bash
bash examples/onboarding/demo.sh
```

Use it to verify controller/evidence plumbing without consuming an LLM call.

### Run the broad Python test surface

```bash
python3 -m unittest discover -s tests -v
```

Some repository areas also use narrower workflows/pytest suites. The applicable CI remains authoritative for the changed scope.

## Before making a change

1. Record `git rev-parse HEAD`.
2. Read `../CURRENT_STATUS.md`.
3. Choose the task lane in `AGENT-BOOTSTRAP.md`.
4. Check whether the path is protected or evidence-sensitive.
5. Define the exact acceptance tests before implementation.

For Factory trust-surface work, read `../status/FACTORY_OWNERSHIP_GATE.md` before editing.

## During implementation

Keep these decisions host-owned:

- verification;
- evidence issuance and binding;
- budgets/policy;
- filesystem/tool authorization;
- termination;
- integration/accepted state;
- release/merge authority.

Workers and models can propose candidates, diagnoses, patches, plans, and evidence requests. They do not self-certify acceptance.

## Qualification ladder

Use the narrowest applicable ladder; do not skip directly to a broad claim.

1. **Static/local sanity** — parsing, formatting, deterministic unit tests.
2. **Subsystem regression** — provider/Station/Factory/enterprise/WebVM tests.
3. **Negative-path/adversarial** — malformed, timeout, denial, budget, replay, death/cancellation, trust-boundary cases.
4. **Exact-head CI** — required workflow runs on the current PR SHA.
5. **Environment-specific qualification** — capable runner, clean install, browser/device, live provider, soak, or external evidence when the claim requires it.
6. **Maintainer attestation** — exact-head approval after the final commit.
7. **Merge/release** — only after applicable gates are satisfied.

A result at one rung does not automatically satisfy a higher rung.

## Exact-head governance

Current solo-maintainer merge flow:

```text
implementation
  → automated qualification/review
  → exact-head maintainer attestation
  → merge
```

Attestation syntax:

```text
RESIDUAL-MAINTAINER-APPROVAL: <full-current-head-sha>
```

Any new commit makes the prior attestation stale.

Canonical policy: `../governance/SOLO_MAINTAINER_POLICY.md`.

## Status vocabulary

| State | Meaning |
| --- | --- |
| PASS | The declared condition was established for the bound revision/environment |
| FAIL | The declared condition was tested and failed |
| UNKNOWN | Evidence cannot establish the condition |
| BLOCKED | A prerequisite/environment/policy prevented the condition from being tested or established |

Never translate a missing check, unavailable environment, provider error, skip, draft implementation, or scaffold into PASS.

## Troubleshooting routes

| Symptom | Canonical route |
| --- | --- |
| Provider/protocol failure | `../triage/provider-protocol-json-fallback.md` + `../station/MODULAR-LAYERS.md` |
| Station behavior | `../station/RUN-CONTROL.md` / `../station/VALIDATION.md` |
| Clean install | `../status/CLEAN_INSTALL_QUALIFICATION.md` |
| Factory ownership/protected path | `../status/FACTORY_OWNERSHIP_GATE.md` |
| M4 runner prerequisites | `../m4-qualification-runner-prereqs.md` |
| Enterprise incident/runbook | `../enterprise/governance/runbooks/` |
| Security review | `../security/` |
| CI/CD architecture | `../architecture/ci-cd.md` |
| Incident response | `../architecture/incident-response.md` |
| Current claim/status question | `../CURRENT_STATUS.md` |

## Release documentation

Before a public release, reconcile:

- `../CURRENT_STATUS.md`
- `../release/`
- `../security/`
- `../status/`
- `../governance/`
- `../../implementation-status.yaml`
- exact-head workflow results and retained evidence

Avoid “production ready” as a blanket label. State which surfaces, environments, and evidence are actually qualified.
