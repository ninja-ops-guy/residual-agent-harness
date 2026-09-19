# RESIDUAL Copilot Studio enterprise deployment

This directory is the source-of-truth configuration for the Power Platform/Copilot Studio package. Microsoft Copilot Studio custom agent templates are distributed as Power Platform solution ZIPs; the final ZIP must be exported from the target/dev Power Platform environment because solution component identifiers and connection references are tenant-owned.

## Native-first deployment

1. Register the RESIDUAL API in Microsoft Entra and expose the delegated `access_as_user` scope.
2. Configure the Copilot Studio custom connector from `residual/integrations/copilot_studio/openapi.yaml` using Microsoft Entra delegated authentication/OBO.
3. Configure the environment variables in `environment.example.json` with real tenant/app/group IDs. Never commit secrets.
4. Create/import the five custom agents represented under `agents/`. Keep knowledge retrieval, topics, generative orchestration, and connection references native to Copilot Studio.
5. Put all components in the `ResidualEngineeringAgents` Power Platform solution.
6. Export the solution as managed for production and import it through normal Power Platform ALM/pipelines.
7. Optionally register the exported solution ZIP as an Inactive custom template in Copilot Agent Kit Agent Library, validate it in a test environment, then activate it for makers.

## Required security configuration

- Conditional Access/MFA/device compliance remain Entra controls.
- The RESIDUAL API validates tenant, audience, delegated scope, RS256 signature, user object ID, department group IDs, and expected connector client application ID independently.
- Group overage uses the fixed Microsoft Graph resolver and configured group IDs; token-provided endpoints are ignored.
- Power Platform DLP should allow only approved Microsoft services plus the RESIDUAL custom connector in the engineering environment.
- Production secrets/keys belong in platform secret/KMS facilities, not solution environment variables.
- External writes remain prohibited until RESIDUAL exact-head HITL approval is implemented for that action.

## Agent Library

As of the 2026 Agent Library model, custom Copilot Studio templates are Power Platform solution ZIPs. Agent Library installs the solution into the selected environment and resolves connection references during install. Treat the exported solution ZIP as a release artifact and bind its SHA-256 into the RESIDUAL enterprise-readiness evidence bundle.
