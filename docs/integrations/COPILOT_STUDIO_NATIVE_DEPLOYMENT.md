# Native Copilot Studio deployment model

Status: design + tenant deployment guide
Target: RESIDUAL Engineering custom agents in Microsoft Copilot Studio

## Native-first rule

RESIDUAL is an execution, verification, evidence, and authority boundary behind
Copilot Studio. The Microsoft layer remains responsible for the user-facing
agent, generative orchestration, native knowledge/tools, connection references,
sharing, solution ALM, and Power Platform governance.

Current Microsoft references:

- Custom agent templates are Copilot Studio agents packaged as Power Platform
  solutions:
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/kit-agent-library-custom-agent-templates
- Custom templates can be published in Agent Library:
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/kit-agent-library-custom-templates
- Agents can be exported/imported through Power Platform solutions:
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-solutions-import-export
- Copilot Studio solutions support environment movement and ALM:
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-solutions-overview
- Generative orchestration selects tools, topics, knowledge, and agents:
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/generative-orchestration
- Agent chat access can be shared with Entra security groups:
  https://learn.microsoft.com/en-us/microsoft-copilot-studio/admin-share-bots
- Environment-group rules can centrally control agent viewer/editor sharing and
  other governance:
  https://learn.microsoft.com/en-us/power-platform/admin/environment-groups-rules

## Solution topology

Use a shared integration dependency plus one department agent solution per
department.

```
RESIDUAL Engineering Integration
  custom connector / API connection reference
  environment variables
  setup documentation

RESIDUAL Firmware Engineering
  custom agent
  RESIDUAL connector tool
  native knowledge slots
  department instructions

RESIDUAL Mechanical Engineering
RESIDUAL Electromechanical Engineering
RESIDUAL Automated Testing
RESIDUAL Quality Assurance Engineering
```

The department solutions SHOULD reference the shared RESIDUAL connector rather
than cloning the connector definition five times.

Do not fabricate a Power Platform solution ZIP in this repository. A native
solution must be authored/imported in a real Power Platform environment and
exported by Microsoft tooling. The repository keeps the authoritative
OpenAPI/profile/configuration and qualification requirements. Once the agent is
authored in the tenant, export the actual solution and preserve its version/hash
as deployment evidence.

## Agent Library lifecycle

Each department profile contains an intended solution name and Agent Library
publish status.

1. Author the agent in a development Power Platform environment.
2. Add it to its custom solution.
3. Add the RESIDUAL custom connector tool/connection reference.
4. Configure the agent to use end-user authentication/OBO.
5. Add only native knowledge sources appropriate to that department.
6. Keep the custom Agent Library template **Inactive** through development,
   security review, and UAT.
7. Export the solution through Microsoft tooling.
8. Import into the test environment and reconfigure authentication/connection
   references as required.
9. Run the RESIDUAL qualification and department access tests.
10. Publish the agent and share chat access with the department's Entra security
    group.
11. Only after qualification, upload the exported solution ZIP as an Active
    custom Agent Library template if centralized self-service installation is
    desired.

Changing Agent Library visibility does not alter RESIDUAL authorization.

## Copilot Studio authoring contract

For each agent:

- **Orchestration:** use Copilot Studio generative orchestration. Do not build a
  duplicate RESIDUAL intent router.
- **Tool:** add the RESIDUAL custom connector using the OpenAPI contract checked
  into this repository.
- **Authentication:** end-user Microsoft Entra/OBO. A maker credential is not
  accepted as equivalent backend authorization.
- **Knowledge:** keep SharePoint/connector/Dataverse or other approved knowledge
  in Copilot Studio. RESIDUAL does not copy it into a second RAG system merely
  for this integration.
- **Instructions:** describe department purpose and tell the agent to select
  only available approved tools. Instructions are usability guidance, not an
  authorization boundary.
- **Error handling:** present RESIDUAL 401/403/409/429 responses as bounded
  authorization/retry guidance; never ask the model to work around a denial.
- **Confirmation:** Copilot-side confirmation may improve UX, but a RESIDUAL
  HITL requirement remains independently authoritative.

## Environment variables / deployment substitutions

The tenant deployment should provide environment-specific values rather than
committing production identifiers:

- RESIDUAL API base URL
- Entra tenant ID
- RESIDUAL API application/client ID and audience
- custom connector client ID
- delegated scope (pilot: `access_as_user`)
- department Entra group object IDs and/or app roles
- department agent chat security-group IDs
- department maker/editor security-group IDs
- native knowledge-source references
- approved RESIDUAL resource-catalog identifiers

The example GUIDs in repository profiles are fixtures, not deployment values.

## Dev / test / production

### Development

- unmanaged authoring is acceptable;
- department templates remain Agent Library Inactive;
- only synthetic/non-production resources are in the RESIDUAL catalog;
- maker and chat-user roles remain separate.

### Test / UAT

- import the solution using normal Power Platform ALM;
- use the test Entra app registrations/groups;
- enforce end-user OBO;
- run positive department and negative cross-department tests;
- run malicious-prompt, replay, evidence, and cancellation qualification;
- validate the exact imported connector/environment-variable configuration.

### Production

- deploy the qualified solution version;
- use production app registrations and stable group object IDs/app roles;
- apply environment-group sharing/governance rules where appropriate;
- publish/share only to intended department security groups;
- preserve export/import hashes and RESIDUAL release evidence;
- no local maker edits should become an unreviewed production authority change.

## Hybrid Entra device model

A compliant hybrid Entra joined Windows device is an upstream Microsoft trust
signal. Conditional Access/device-compliance policy determines whether Microsoft
issues/allows the session/token according to tenant policy.

RESIDUAL validates the API token and its authorization claims. It MUST NOT claim
that it independently attested the Windows device merely because the call
arrived from Copilot Studio.

A future explicit device-claim integration would need its own issuer, claim,
freshness, replay, and policy specification before it could become RESIDUAL
evidence.

## Native features intentionally not rebuilt

- Copilot Studio generative orchestration;
- Copilot Studio topics, tools, knowledge, connected agents, and workflows;
- Power Platform solution import/export/pipelines;
- Agent Library discovery/template distribution;
- Entra sign-in and Conditional Access;
- security-group agent sharing;
- environment-group governance/DLP controls;
- native Microsoft knowledge/connector permission enforcement.

RESIDUAL remains the independent bounded-execution and evidence layer.
