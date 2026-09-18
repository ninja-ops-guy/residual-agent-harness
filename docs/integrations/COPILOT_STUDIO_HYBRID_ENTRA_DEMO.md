# Hybrid Entra joined Copilot Studio demo walkthrough

Status: tenant-ready walkthrough + deterministic repository fixture

The executable repository fixture is:

```bash
python examples/copilot_studio/hybrid_entra_demo.py
```

It uses a locally signed OIDC token with Entra-shaped claims and exercises the
actual RESIDUAL Copilot gateway and Firmware Factory handoff. It deliberately
does not claim to contact Microsoft, validate Conditional Access, attest a
Windows endpoint, start Factory worker code, or issue a Station receipt.

## Intended enterprise environment

The live walkthrough assumes:

- a corporate Windows endpoint is hybrid Microsoft Entra joined;
- the endpoint is managed and considered compliant by the organization's device
  management policy;
- Conditional Access requires the intended device/user conditions and MFA;
- the Firmware user is a member of the configured Firmware agent chat group and
  the RESIDUAL Firmware authorization group/app role;
- a Mechanical user is not a member of the Firmware RESIDUAL authorization
  group/app role;
- the Copilot Studio custom agent is deployed through a Power Platform solution;
- the RESIDUAL custom connector uses end-user Entra/OBO authentication;
- the RESIDUAL API validates exact issuer/audience, delegated scope, tenant,
  immutable user object ID, calling client, and department authorization.

Device compliance is a Microsoft upstream control. RESIDUAL must not describe
itself as independently attesting the endpoint unless a separately implemented
device-claim integration exists.

## Demo A — positive Firmware user

### 1. Establish Microsoft session

On the managed corporate device, sign in with the Firmware test account through
the normal organization sign-in path. Confirm in Microsoft administration
evidence that the intended Conditional Access policy applied and the sign-in was
allowed.

Do not copy access tokens into screenshots or demo notes.

### 2. Open the department agent

Open **RESIDUAL Firmware Engineering** from the intended Copilot Studio /
Microsoft 365 channel.

The user should have chat access because of the configured Entra security group.
Chat access alone is not backend authority.

### 3. Ask for a bounded analysis

Example user request:

> Analyze the approved firmware repository for the reported startup defect.
> Do not change source files. Show me the evidence and anything that still needs
> human review.

Expected Copilot behavior:

1. Generative orchestration selects the RESIDUAL mission tool.
2. Copilot supplies only the approved structured template inputs such as
   `repository_id` and `analysis_profile_id`.
3. The connector obtains/passes the delegated end-user token.
4. RESIDUAL independently validates the token and department policy.
5. RESIDUAL returns a prepared mission ID/state.

The agent must not manufacture a success answer if RESIDUAL returns a denial.

### 4. Observe the RESIDUAL authority boundary

For the first pilot, the prepared mission should map only to
`firmware-repository-analysis`.

The Factory handoff must resolve the opaque repository ID through the server
resource catalog and produce a WorkerContract that:

- reads only approved repository selectors;
- binds an immutable Git input commit;
- permits one declared analysis report output;
- allows only the brokered `read_file` and `write_file` tools;
- forbids `network` and `shell`;
- does not permit source-tree writes;
- does not auto-create a FrozenPlan approval;
- does not claim a Station receipt before execution + verification.

### 5. Evidence shown to the user

Once a later execution layer is enabled, the Copilot response should display
the bounded outcome plus evidence/receipt references. It should clearly
distinguish:

- prepared;
- running;
- approval required;
- verified/complete;
- failed;
- cancelled.

The current read-only handoff demo intentionally stops at **prepared** and does
not fabricate later states.

## Demo B — Mechanical user attempts Firmware mission

Sign in from the same class of managed/compliant device as the Mechanical test
user and open the Mechanical department agent.

If the Mechanical agent or user attempts to invoke the Firmware mission
directly, the expected backend result is:

```
403 department_denied
```

No Firmware mission/evidence metadata should be leaked.

Copilot Studio sharing is not relied upon as the sole protection; RESIDUAL
independently enforces the token's department authorization.

## Demo C — Firmware access removed after mission creation

1. Create a Firmware mission with an authorized Firmware identity.
2. Remove/revoke the user's Firmware backend group/app-role assignment.
3. Obtain a **new token** after the identity change. Do not assume an already
   issued token instantly changes.
4. Attempt to inspect/cancel/read evidence for the prior mission.

Expected result with the new token:

```
403 department_denied
```

This demonstrates authorization freshness at every gateway operation.

## Demo D — wrong connector client / wrong scope

From a test client registration that is not the approved Copilot connector
client, call the RESIDUAL API using an otherwise valid user token.

Expected:

```
403 client_denied
```

Repeat with a token that lacks the delegated RESIDUAL scope:

```
403 scope_denied
```

These checks demonstrate that a signed token is necessary but not sufficient
authority.

## UAT evidence package

Capture the following without recording credentials/tokens:

- imported Power Platform solution version;
- department agent name and environment;
- custom connector/connection reference configuration identifiers;
- Entra tenant/client/group object IDs used by the test deployment;
- Conditional Access sign-in result from Microsoft administration logs;
- RESIDUAL release/head SHA;
- RESIDUAL policy hash;
- resource catalog hash;
- mission ID and revision ID;
- Factory plan and WorkerContract hashes;
- negative-test error codes;
- later, Station receipt/evidence hashes when execution is enabled.

## Exit conditions before publishing Agent Library template Active

- exact imported solution version has passed UAT;
- OBO uses the intended delegated end-user identity;
- positive Firmware walkthrough passes;
- Mechanical cross-department denial passes;
- group/app-role removal + refreshed-token denial passes;
- wrong-client and wrong-scope tests pass;
- no production write/merge/shell/arbitrary-network authority exists in pilot;
- exact RESIDUAL PR heads have passed repository qualification;
- security review has no unresolved High finding;
- agent is then published/shared only to intended groups;
- Agent Library custom template can move from Inactive to Active after those
  controls are evidenced.
