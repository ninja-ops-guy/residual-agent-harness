# Integration Skills

These are reusable agent workflows. A “skill” here is an operating recipe, not additional acceptance authority. Every skill inherits the repository's verifier-first and exact-revision rules.

## Skill: `residual.setup.station`

**Use for:** getting a new operator or agent to a working Command Station.

**Read:** `../../START-HERE.md` → `../station/ARCHITECTURE.md` → `../station/VALIDATION.md`.

**Procedure:**

1. Choose Docker or native mode.
2. Launch Station.
3. Run the scripted training mission before adding credentials.
4. Configure a provider in Model Workshop.
5. Test the connection.
6. Inspect Diagnostics/Observation Console.
7. Only then attach a real project.

**Success condition:** Station is reachable, scripted training completes, and any provider connection is reported according to its actual outcome.

**Do not claim:** blank-environment qualification, live-model quality, or production readiness merely because setup succeeded.

---

## Skill: `residual.provider.configure`

**Use for:** OpenAI, OpenAI-compatible endpoints, Anthropic, Gemini, Azure OpenAI, AWS Bedrock, or Ollama already supported by the modular provider layer.

**Read:** `../station/MODULAR-LAYERS.md`.

**Procedure:**

1. Configure provider/model in Model Workshop or the documented environment variables.
2. Keep local and cloud routing explicit; local failure must not silently become cloud egress.
3. Save routes before testing.
4. Run a connection test/playground call.
5. Inspect normalized provider outcome and observation/accounting records.
6. Verify failover behavior only for errors the router is designed to advance past.

**Security constraints:** secrets stay out of task packets/exports/observations; redirects are refused by built-in HTTP adapters; transport/accounting failures remain failures.

---

## Skill: `residual.provider.add`

**Use for:** adding a new transport/provider.

**Read:** `../extending.md`, `../station/MODULAR-LAYERS.md`, existing `../../ai_providers/adapters/` implementations and tests.

**Procedure:**

1. Define the protocol and capability boundary before code.
2. Reuse the registry/router instead of bypassing it.
3. Normalize auth, timeout, rate-limit, server, malformed-output, and unsupported-operation errors.
4. Bound request/response/frame sizes and redirects.
5. Keep usage `reported`, `modeled`, and `unknown` distinct.
6. Add deterministic protocol fixtures and negative-path tests.
7. Add live-provider evidence only when explicitly run; fixtures do not substitute for it.
8. Update canonical provider docs and this wiki only after behavior exists.

**Stop if:** the adapter needs to grant model-requested tools or acceptance authority. Design a host-owned capability boundary instead.

---

## Skill: `residual.extension.add`

**Use for:** custom checks, local solvers, task types, or trusted Python plugins.

**Read:** `../extending.md` and `../module-tutorial.md`.

**Core rule:** a solver result is still independently checked. Check revisions remain explicit cache inputs. Plugins are trusted host code, not model-generated sandboxed code.

**Validation:** include malformed input, undeclared evidence/dependency access, duplicate/unknown updates, and exception paths where applicable.

---

## Skill: `residual.enterprise.connect`

**Use for:** ITSM, ticketing, CI/CD, communications, monitoring, or future enterprise connectors.

**Read:** `../enterprise/README.md`, `../enterprise/ENTERPRISE_SPECS.md`, `../enterprise/TRACEABILITY.md`, `../../residual/integrations/`.

Current integration modules are organized under:

- `residual/integrations/ticketing.py`
- `residual/integrations/itsm.py`
- `residual/integrations/cicd.py`
- `residual/integrations/comms.py`
- `residual/integrations/monitoring.py`
- `residual/integrations/base.py`

**Procedure:**

1. Map the requested connector to an enterprise requirement and role boundary.
2. Define credentials, tenant scope, read/write actions, rate limits, audit events, and failure semantics.
3. Default to least privilege and explicit human/host authorization for mutating actions.
4. Add traceability from requirement → implementation → test.
5. Exercise deny, timeout, malformed response, auth failure, cross-tenant, and replay/idempotency cases as applicable.
6. Document operator setup in the canonical enterprise runbook.

---

## Skill: `residual.swarm.attach`

**Use for:** attaching another worker/runtime/agent family to RESIDUAL.

**Read:** `../factory/PLAN-CONTRACT.md`, relevant `../factory/` docs, `../swarm/`, and `../status/FACTORY_OWNERSHIP_GATE.md`.

**Procedure:**

1. Treat the external agent as a worker, not an integrator/verifier.
2. Give it a bounded worker contract, permitted evidence, tools, filesystem, resources, and output protocol.
3. Preserve host-owned termination, evidence issuance, verification, and deterministic integration.
4. Record worker identity/provenance in the evidence path.
5. Test malformed output, forbidden tool/filesystem access, transport death, cancellation, budget exhaustion, duplicate/replayed output, and late results.
6. Benchmark utility after correctness/safety gates pass.

**Do not infer:** that more agents improve quality or efficiency until a governed comparison measures it.

---

## Skill: `residual.research.run`

**Use for:** benchmarks, experiments, Arena-aligned/internal comparisons, or paper evidence.

**Read:** `../research.md`, `../evaluation.md`, `../controlled-evaluation.md`, `../measured-eval-binding.md`.

**Procedure:**

1. Freeze workload/protocol/evaluator before the confirmatory run.
2. Bind source SHA, environment, provider/model identity, budgets, seeds/repetitions where relevant, verifier policy, and output artifact hashes.
3. Keep development/apparatus runs distinct from scientific results.
4. Preserve failures and negative controls.
5. Report `UNKNOWN` when the experiment cannot establish the target claim.
6. Never describe an internal “aligned” scaffold as official third-party participation or a leaderboard score.

---

## Skill: `residual.release.qualify`

**Use for:** preparing a PR/release for merge.

**Read:** `OPERATIONS.md`, `../governance/SOLO_MAINTAINER_POLICY.md`, `../CURRENT_STATUS.md`.

**Procedure:**

1. Identify exact PR head.
2. Run scope-appropriate local tests.
3. Wait for exact-head required CI/qualification.
4. Inspect security/protected-boundary evidence.
5. Record unresolved unknowns without laundering them into PASS.
6. After final head is stable, maintainer attests exactly:
   `RESIDUAL-MAINTAINER-APPROVAL: <full-current-head-sha>`
7. Any new commit invalidates that attestation.

A release is evidence-bounded. Passing one lane does not imply unrelated environments or claims passed.
