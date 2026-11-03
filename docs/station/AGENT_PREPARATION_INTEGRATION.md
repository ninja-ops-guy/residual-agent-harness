# Bounded Station preparation integration

Draft child of #562 at 8321504d4b72ea8a9c6c0b8f3eb241b00afcf0d8.
The original standalone component and its retained 29-model/17-browser evidence
remain bound to that source. No native qualification or release acceptance.

## Architecture and ownership disposition

Station uses one hash router (`names`, `state.view`, `render`) in app.js, one
project selector, one polling loop and an explicit static asset allowlist.
Use that router for #preparation. No second router, global preparation store,
API endpoint, health polling or authenticated observation bridge is introduced.
The component owns only its DOM and in-memory declarations. Each render destroys
the old view; a generation check rejects late module loads. Switching projects
clears declarations before asynchronous refresh; route exit and reload discard them.
The form remains accessible without a selected project. No Station token, job,
project state or telemetry is copied into the component.

#349 remains an open separate Shared Comms lane at 625e1ce97919098dbe9d586ffcaf4b2a94257184.
It overlaps app.js and server.py. Its chat, roster, planning and authority-banner
work is not merged or reproduced here. #471 at 9f8702e1069e04be0d8298003a1beb48493ff265
requires operation completion, task outcome and accepted evidence to stay distinct;
the preparation view explicitly states that boundary and reads none of those as
agent authority. Existing worker-access controls are untouched.

#562 records Kimi reporting no designated Station UI/app.js seat or overlapping
work on record. Public metadata/comments provide no newer ownership lease and
cannot establish absence of private work. Therefore this change is a stacked
draft for the existing preparation lane, not a write into #349, #559, #561, main
or a claimed exclusive UI ownership assignment. Reconcile these exact small
router/static-server hunks with any private UI owner before composed integration.

## Trust boundary

All eight reducer stages remain unchanged. UI exposure does not authenticate
reports. Missing, expired, future, contradictory and mismatched observations
cannot establish enrollment authority, eligibility or acceptance. No reports are
loaded by this Station adapter at all; its initial input is empty. Declared labels
remain unverified. Station online is explicitly the browser connection, not agent
connectivity. No enrollment, execution, containment probe, credential import,
persistence, evidence receipt or mission-acceptance mutation is added.

The historical standalone documentation continues to describe the isolated
component. In this candidate only, the Station wrapper replaces its preview
notice after mount. It does not change the reducer's integrated=false qualification
marker into a readiness claim.

## Verification and limitations

Commands:

    node --check residual/station/static/app.js
    node --test tests/agent-preparation.test.mjs
    python -m unittest discover -s tests/station -p test_station.py
    python -m unittest discover -s tests/station -p test_agent_preparation_assets.py
    node tests/agent-preparation-station-browser.cjs

The additional browser harness starts a disposable real loopback Station, uses
normal clicks, records requests/errors and captures desktop/compact screenshots.
It does not enroll agents or call providers. Missing browser binaries are a
qualification failure/blocker, never a pass. Existing standalone browser evidence
is preserved; it does not qualify this wrapper. Multi-host onboarding, native
containment, Shared Comms qualification, exact-head review and composed production
qualification remain separate. V1_RELEASE_HOLD remains active.
