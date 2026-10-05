# MC-V1-001 validation and claim boundary

## Executed locally

Python 3.13.5, Node 22.16.0, Linux.

`python -W error::ResourceWarning -m unittest discover -s tests/mission_sync -v`

**52 distinct tests passed**, no skips. Includes actual delivered Python/Node
client code over real loopback HTTP against a real SQLite Station-schema
fixture. The fixture has the documented Station project/task tables; it is
**not the full Station service**. Native hook tests use the delivered Hermes
and OpenClaw plugins with API-shaped fixture hosts; they are not installed
Hermes/OpenClaw gateways. No model/provider was called.

Coverage includes false acceptance reports, forbidden fields/kinds, exact
replay receipts, conflicting IDs, gaps/types, restart persistence, concurrent
duplicate submissions, expiry/revocation, clock rollback, stale attempt/spec,
cross-task/project/token boundaries, no token/lease/path projection, two-ended
sharing consent, scoped echo handling, ACK scope/hash checks, changed canonical
state, transaction rollback on an injected fanout failure, drainable
backpressure, journal chain/pagination, malformed JSON, local spool separation,
server ACK loss, receive-before-ACK, and Python/Node Unicode hash parity.

Two offline Chromium viewport fixtures (1440×1100 and 390×844) passed task,
binding, unverified-report rendering, no-overflow, private-sharing default and
literal-text XSS checks with no page errors. They used the exact shipped
HTML/JS/CSS and synthetic fetch responses. They are NOT browser-to-live-Station
end-to-end proof. Direct browser navigation to loopback was blocked by the
environment's administrator policy; no policy bypass/change was attempted.
The agent-browser CLI was unavailable, so offline rendering used installed
Chromium through Playwright.

## Repairs found during implementation testing

- A full fanout queue initially prevented poll from creating a snapshot and
  therefore prevented draining. Poll now drains existing deliveries and
  explicitly reports that its latest snapshot is not queued yet.
- A native scope-check call initially consumed local observation context before
  returning it to the model hook. Scope checks now peek without advancing the
  returned-context cursor; injection consumes once.
- SQLite fixture connection context managers initially left OS handles to
  garbage collection. The fixture now explicitly closes every connection;
  ResourceWarning is escalated during the final run.
- The native test module initially re-discovered eight imported HTTP cases.
  The final count is 52 distinct tests, not the earlier 60 executions.

These are author-run checks and an internal self-review, **not independent
acceptance or evidence that no other defect exists**.

## Not established here

Full repository clone/network access was unavailable (GitHub DNS resolution
failed in the execution container); source inspection/publication uses the
connected GitHub API. The real-Station regression in
`tests/test_station_mission_sync.py` and the added exact-head CI workflow are
provided, but were not run locally against a complete checkout. Whole suite,
wheel installation, old entrypoint compatibility, supported matrix, actual
native policy/hook activation and physical host qualification remain open.

The console `residual-station` now selects the additive Mission Control wrapper.
The legacy module `python -m residual.station.server` intentionally remains the
unextended legacy entrypoint. No existing Station state-machine function,
Factory acceptance rule, Shared Comms runtime, OpenClaw control-plane package,
release gate or frozen candidate is changed. Source and test SHA-256 records
are supplied with the owner-delivered implementation archive. New published
HEAD/TREE and any later composed tree require their own exact-head checks.
