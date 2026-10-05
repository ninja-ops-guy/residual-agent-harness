# MC-V1-001 — Mission/AUTH/OpenClaw composition rehearsal

Status: **DRAFT / V1 REQUIRED / NOT RELEASE DESIGNATED / V1_RELEASE_HOLD**.
This is the owner's authorized continuation of Mission Control #524, published
as review PR #527. Closure retains final composition/designation ownership.
Original input branches and accepted main are unchanged. This is not all-v1
convergence and is not authority to activate any native harness or provider.

## Pinned source lineage

| Source | Exact HEAD |
| --- | --- |
| Accepted main | `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2` |
| Mission Control #524 | `ec4df5a734054fd8f2fa0ef32f4061a42f5bdf82` |
| AUTH #519 | `b16482bf589566197d970a30053fd3fea6b628ff` |
| OpenClaw #511 | `7c35f72863e1631d4675c82f459b717a53b53bd9` |

Normal three-way source merges preserve input ancestry; no side was discarded:
- MC + AUTH: `4893b9902ae3a8142babf8c379aaa4e9450ec041`, tree
  `e24f8e01120074eb15c3d81af60863f2308308a0`.
- Add OpenClaw: `d1b76642230157d8cd06366b4f65ce31caf389c9`, tree
  `30689ed18a20ce1ce31fe094374b8ba02ae0c62b`.
- Add actual composition/wheel probes: `5a3707add7c12bb5b3ac92894e5279ba75cce30d`,
  tree `826f3164af16e8a2458290eec0a28849aff07353`.

The shared Station service edits merge cleanly: OpenClaw evidence binding and
AUTH typed rejections both remain. Any repair below creates a new candidate
identity; the final exact HEAD/TREE is recorded externally in the PR and CI
artifacts rather than self-referentially in this document.

## Reproduced defect and bounded repair

First exact-head workflow `37259828352` passed all five composed Station/client
scenarios on Python 3.11 and 3.13, then failed the isolated installed-wheel probe.
The wheel omitted `scripts/check_maintainer_approval.py` and the normative AUTH
spec; `authority_kernel.revision()` raised on the missing script. A real demo
Station task reached review but could not integrate because receipt issuance
requires the kernel revision. Building a wheel and invoking `--help` had not
exercised this path.

The repair bundles the two exact source inputs as inert package data, with an
integrity manifest. Source/editable installs retain source-tree measurement;
wheels resolve their own package inputs. Runtime kernel modules are still
measured from their actual installed files, never copied substitute modules.
Incomplete, malformed, duplicate-key, symlinked or modified packaged inputs fail
closed, without cwd, HOME, environment or neighboring-file fallback. The wheel
probe requires installed/source kernel identity equality and rejects deletion of
the packaged spec before restoring it and exercising task integration.

The normative spec, Factory ownership baseline, approval checks and Station
acceptance policy are not changed by this repair. Bundled maintainer-gate source
is data for identity measurement, not permission to run or bypass that gate.

## Reproduction

```sh
python -m pip install -e '.[factory,test]'
python -m pytest tests/test_mission_composed_authority.py \
  tests/qualification/test_authority_kernel.py \
  tests/qualification/test_authority_wheel_inputs.py -v
python scripts/prove_mission_wheel.py --output /tmp/mc-wheel-proof
```

Node 22.16 or later with `node:sqlite` is required. The dedicated workflow pins
Node 22.16.0 and runs Python 3.11 and 3.13. Its checkout must equal the PR head,
contain all three input ancestors, and have no source changes before testing.
The artifact retains exact HEAD/TREE, tracked-source archive, test output, wheel,
wheel SHA-256, source/installed kernel identities, package-origin/hash checks,
and explicitly bounded result flags. Fresh terminal runs on the final candidate
are required; neither old component results nor intermediate results transfer.

Five real-Station scenarios exercise production HTTP handlers, Git-backed demo
tasks, SQLite and the actual Python and Node clients:
1. Two-way observation delivery, replay after Node-process restart, false
   completion not mutating task state, then canonical Station review/integration
   transitions visible through both clients.
2. Full text withheld unless both bound conversations consent.
3. Binding capabilities cannot access operator or worker routes; explicit
   acceptance fields and foreign Origin are rejected.
4. Real repair/retry increments the attempt and invalidates the prior binding.
5. Existing Station routes and the new Mission Control static assets are served.

Demo review is scripted. These tests do **not** establish independent verification,
installed native OpenClaw/Hermes hooks, model consumption, unsolicited native
message sending, or physical process lifecycle guarantees. Python and Node
clients are software interfaces, not proof of two live agent seats.

## Remaining gates — do not silently close

- Factory ownership intentionally rejects the AUTH change to
  `residual/factory/worker_contract.py` against the protected baseline. Do not
  advance it merely to make CI green. Obtain the authorized ownership disposition
  and rerun every dependent qualification on the resulting exact tree.
- The inherited legacy-v2 receipt/current-kernel matching gap is not repaired or
  accepted by this package fix. AUTH/Closure must disposition it explicitly.
- Review fresh terminal repository checks, including failures not explained by
  the ownership gate; no blanket claim that all failures are administrative.
- Obtain independent security/privacy/durability review of the combined source
  and build-time packaging repair.
- On operator-authorized, pinned native installations, prove hook registration,
  correlation, bidirectional context/observations, consent, replay/reconnect,
  revocation and stale-attempt fencing with exact-build evidence.
- Keep OpenClaw native cancellation/restart proof, owner and maintainer approval,
  final release composition and post-merge re-verification as separate gates.

No merge, release tag, auto-merge, provider call, live-host activation, secret
change or acceptance is implied by a passing software workflow.
