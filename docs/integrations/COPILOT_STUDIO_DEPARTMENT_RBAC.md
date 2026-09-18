# Copilot Studio + RESIDUAL department RBAC

Status: design contract
Machine-readable matrix:
`residual/integrations/copilot_studio/departments/rbac.yaml`

## Two independent authorization planes

### Microsoft plane

Microsoft Entra / Copilot Studio controls who can:

- chat with a department agent;
- edit/author the agent;
- import/publish its Power Platform solution;
- satisfy tenant authentication and Conditional Access policy.

Chat access SHOULD be assigned through department Entra security groups.
Maker/editor groups SHOULD be separate from chat-user groups.

These permissions are not RESIDUAL execution authority.

### RESIDUAL plane

RESIDUAL independently evaluates the validated token and server-side policy:

- tenant;
- immutable Entra object ID;
- delegated scope;
- calling client;
- department group or configured app role;
- approved mission template;
- resource catalog;
- risk ceiling;
- HITL requirement;
- evidence visibility.

A user who can chat with an agent but fails RESIDUAL authorization receives a
denial. A Power Platform administrator or Copilot maker receives no engineering
authority merely because that person can edit/deploy the agent.

## Department users

### Firmware Engineering

Pilot status. Only `firmware-repository-analysis` is currently executable
through the dedicated read-only Factory handoff. Sandbox build and test-triage
templates remain planned until their mediated tools and qualification exist.

### Mechanical Engineering

Template/source definition exists, backend execution remains planned.
No Mechanical Copilot request is to be translated into Firmware authority.

### Electromechanical Engineering

Template/source definition exists, backend execution remains planned.
Future cross-domain access must use explicit resource/catalog grants rather than
assuming membership in both parent engineering groups.

### Automated Testing

Template/source definition exists, backend execution remains planned.
Test execution will require its own approved runners, test-suite identifiers,
budgets, artifact boundaries, and cancellation semantics.

### Quality Assurance Engineering

Template/source definition exists, backend execution remains planned.
QA is intentionally modeled as an independent review/evidence role. Cross-
department evidence visibility must be explicitly granted and does not confer
candidate-modification authority.

## Role model

### Department Engineer

Can submit approved missions for the assigned department and inspect/cancel own
missions. Cannot change policy, bypass qualification/verifiers, merge, or gain
production-write authority by prompt.

### Engineering Lead

Can operate within authorized department scope and may hold explicit HITL
approval permission for an allowed external write. Lead status alone does not
bypass verifier, qualification, or trust-boundary gates.

### QA Reviewer

May review specifically authorized cross-department evidence and record
qualification/review decisions. The reviewer must not modify the candidate under
the same independent-review identity.

### Auditor

Read-only evidence/audit verification. No mission submission, cancellation,
candidate mutation, approval, or policy change.

### RESIDUAL Policy Administrator

Manages department policy/resource catalogs. Policy administration does not
self-authorize missions or approvals.

### Copilot Agent Maker

Authors/tests the Microsoft agent and solution. Has no backend RESIDUAL
authority solely by being a maker.

### Platform Administrator

Imports/publishes solutions and manages platform deployment. Infrastructure
administration does not imply engineering authorization.

## Separation-of-duty rules

1. A policy administrator must not self-approve authority created by an
   unreviewed policy change.
2. A QA reviewer must not modify the candidate being independently reviewed
   under the same review identity.
3. Copilot maker/editor privileges are never accepted as RESIDUAL capability
   grants.
4. Platform administration is not department engineering authority.
5. No role can bypass verification/qualification via prompt, Copilot
   confirmation, solution ownership, or environment administrator status.

## Department assignment

Each department descriptor has two Entra security-group IDs:

- `chat_security_group_id`: who may chat with that custom agent;
- `maker_security_group_id`: who may author/test the department solution.

Production deployments replace fixture GUIDs with stable Entra object IDs.
RESIDUAL's runtime department authorization uses its independently configured
allowed group/app-role IDs and remains fail closed if the token lacks them.
