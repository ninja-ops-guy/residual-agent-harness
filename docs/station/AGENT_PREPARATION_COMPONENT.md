# Isolated Agent preparation component

This component is **not integrated into Station and not native-qualified**.
It is a read-only prerequisite for the GUI onboarding acceptance described in
[the owner's clarification](https://github.com/ninja-ops-guy/residual-agent-harness/pull/534#issuecomment-6532395026).
It creates no identity, enrollment, task, credential, evidence receipt or authority.

## Source and ownership

Built on frozen #559 source e1abfa11a1539e82955b652c4c98f163045e9a4c,
tree 669f40017db0a04a366942b3488438ad7afea1d6. Only new scoped files are added.
Existing app.js, Station routes, state, styles, authority policy, Factory pins,
licensing boundaries and existing workflows are unchanged. This owner-opened
product task does not expand the Apache Open Core manifest. No human DCO
sign-off, independent acceptance or release approval is supplied by the agent.

Before integration, reconcile the active Station UI owner and app.js overlap
with #349 and reuse #471's operation-versus-task/evidence distinctions. Public
unassigned PR metadata is not a current ownership lease. #527 mission hooks
and #281/#289/#349 chat work remain separate lineages, as do #529 and #561.

## Explicit presentation input

The pure reducePreparation(input, nowSeconds) function accepts plain JSON data:

- intended: optional declaration fields worker_id, host_id, seat_id,
  process_instance_id, profile_id, workspace, project_id, adapter,
  adapter_version, source_revision, wheel_sha256, capabilities.
- preflight: optional existing mesh_cli.worker_main --preflight result:
  status PREFLIGHT_PASS, adapter discovery, project_id and worker_id.
- adapterDiscovery: optional existing OpenClawExecAdapter.discover result.
- meshStatus: optional existing MeshState.status result with schema
  residual.sc.mesh.status/1 and qualification health_only_not_mesh_qualification.
- nowSeconds is an explicit display clock in epoch seconds, not a trusted
  receipt timestamp or authorization clock.

These are supplied observations, not authenticated reads or proof types. No
new acceptance/eligibility/ACK/receipt schema is introduced. Unsupported input
remains unknown. Fields have presentation size/shape bounds; those bounds do
not amend backend admission or privacy/retention policy. Reports have no trust
provenance in this standalone component.

Eight independent stages are shown: identity preparation, adapter preflight,
Station connectivity, owner enrollment, two-way communications, native
containment, mission eligibility and mission acceptance.

DECLARED means unverified owner input. REPORTED means only that a supported
local/snapshot shape was supplied and its available labels agree. It is never
PASS, accepted, current authority or readiness. Reports may be stale. Preflight
has no timestamp, host/workspace/source/wheel binding. Health status exposes
project_count, not selected project IDs. READY, counters, foreign cursors and
transport ACK cannot supply selected membership, communications qualification
or mission acceptance. Unavailable seat/process/profile/workspace/package
bindings remain explicitly unbound. Matching labels do not authenticate a host.

Expired/revoked/mismatched/unsupported reports are distinguished without
promoting any other stage. Unknown status and contradictory local reports
remain uncertain. No age threshold, authority policy or new proof category is
invented. Ordinary Station verification and independent acceptance remain
necessary outside this component.

## Isolated view

mountAgentPreparation(root, input, optionalClock) renders accessible form fields,
unverified declaration text and eight status cards. Review declarations only
updates in-memory presentation. Clear removes all declarations and observations.
update replaces input rather than merging prior identity; destroy removes the
view and listeners. Reload starts empty.

The view performs no fetch, authenticated call, storage, cookie write, config
import, native discovery, execution, enrollment, mutation or external service
connection. There are no credential fields. Unsupported credential/config keys
are rejected without echo. Arbitrary secrets cannot be recognized if deliberately
placed in a permitted text label; do not enter credentials or private profile
contents. Text is rendered through DOM textContent/value, never HTML parsing.

## Verification

Run pure model tests with:

    node --test tests/agent-preparation.test.mjs

Use the repository's pinned Playwright tooling for the standalone browser:

    npm install --ignore-scripts --no-audit --no-fund
    npx playwright install chromium
    node tests/agent-preparation-browser.cjs

The browser harness serves only six allowlisted synthetic/static files on a
task-owned loopback port; it does not start Station. It uses normal unforced
Playwright click/fill interactions, captures screenshots and raw results,
rejects unexpected requests, and instruments network/persistence APIs.
The dedicated Ubuntu 24.04/Node 22 workflow retains failures as well as successes.
Results include source hashes, checked-out head/tree, run/attempt and runtime.

Tests cover missing/expired/future/mismatched/cross-project reports, revoked and
uncertain states, unsupported platforms, unsupported proof/credential fields,
hostile and oversized text, clear/reload isolation, and absence of network or
persistence effects. No source/mock/browser result qualifies real agent
onboarding, installed packages, native containment, multi-host continuity,
social import/sync, or a final composed release. V1_RELEASE_HOLD remains active.
