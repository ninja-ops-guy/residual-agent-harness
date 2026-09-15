# Traceability and documentation consistency audit

Audit base: `50646c93ff5772e9ee1182ca6b4c290b1a5e7cba` (latest merged `main`
observed during reconciliation, including PR #81 and PR #42).

Scope: status, traceability tests, current-state prose, and issues #28-#35.
The M4 trust-boundary implementation and shared evidence schemas were treated
as protected and were not modified.

## Outcome

- The manifest is the machine-readable status authority and its generated
  projection matches byte-for-byte.
- M2, M3, M4, EVAL, SWARM-EVAL, VQ, DSM and CIC are represented as implemented
  mechanisms with canonical code and test paths.
- M5 and GCP are represented as partial: meaningful implementation exists, but
  their documented production/integration boundaries remain open.
- STUDIO and N9 remain partial; present stubs, development harnesses, and
  unexecuted live qualification are not treated as complete requirements.
- No current-state documentation contradiction was reported by the scanner.

The complete requirement-family audit table is the generated
[`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md). It lists all 45
families, authoritative status, specification, canonical code paths, and mapped
test paths. The notes section records the remaining work and non-claims for
every partial or research-facing surface.

## Status diff

| Measure | Before | After |
|---|---:|---:|
| Families | 39 | 45 |
| Implemented | 22 | 27 |
| Implemented, closure unverified | 1 | 0 |
| Partial | 12 | 14 |
| Not started | 4 | 4 |

| Family | Before | After | Audit decision |
|---|---|---|---|
| M4 | implemented_unverified | implemented | PR #81 closed the enumerated implementation gaps and added verified-tree binding, filesystem safety, isolated verification, typed Git evidence and adversarial tests. |
| SWARM-EVAL | absent | implemented | PR #86 implements EVAL-R1-R10 and retains hash-bound R0-R5 fixture evidence. |
| VQ | absent | implemented | The merged VQ package maps VQ-R1-R9 and demonstrates the degraded-quality fail-closed gate. |
| DSM | absent | implemented | PR #42 maps DSM-R1-R10 and retains recovery/fault evidence for the documented single-writer boundary. |
| M5 | absent | partial | Host-owned loop mechanisms exist; production Factory adapter/live multi-iteration qualification remain open. |
| GCP | absent | partial | Foundational governance models exist; full runtime enforcement, quorum approvals and Evidence Fabric projections remain open. |
| CIC | absent | implemented | The opt-in structural integration and paired scripted evaluation are implemented and tested; no live superiority claim is made. |
| M3 | implemented | implemented | Removed stale references to the now-closed M4 Git-evidence gap. |
| STUDIO | partial | partial | Removed stale M4 blocker while preserving the frontend/IDE prototype distinction. |
| N9 | partial | partial | Added existing soak and cluster paths; kept partial because the required live 30-day soak and all original onboarding details are incomplete. |

All unchanged families were revalidated for status vocabulary, path existence,
required tests for implemented states, and explicit canonical paths for
`not_started` states.

## Issue #28-#35 reconciliation

| Issue | Disposition | Evidence or remaining work |
|---|---|---|
| #28 EVAL-001 | Closed | PR #86, `tests/swarm/test_eval_frozen.py`, and retained `evidence/eval/` artifacts satisfy the fixture acceptance boundary. |
| #29 VQ-002 | Already closed | Merged VQ code/tests and retained benchmark demonstrate profile updates and fail-closed escalation. |
| #30 OTX-003 | Narrowed | Existing Bayesian task-class controller retained; open work is decomposed timings, decision observations, deployment threshold, FrozenWorkload integration, and two-class acceptance evidence. |
| #31 DSM-004 | Closed concurrently, evidence reconciled | PR #42, `tests/swarm/test_dsm.py`, and `evidence/dsm/dsm-004-evidence.json` satisfy the documented single-writer acceptance boundary. |
| #32 RUNTIME-005 | Narrowed | Existing engines/async primitives retained; open work is shared two-adapter conformance, faulted cancellation proof, canonical Factory/eval metadata propagation, and integrated fail-closed acceptance. |
| #33 OBS-006 | Narrowed | Existing Prometheus/SLO/correlation mechanisms retained; open work is authoritative raw-observation reconstruction, decomposed timings, completeness alongside aggregates, schema/hash binding, and deterministic report reproduction. |
| #34 PROD-007 | Narrowed | Existing HITL/resume/HADR components retained; open work is the integrated restart/replay/secret/backpressure/shutdown/migration/runbook acceptance proof. |
| #35 RESEARCH-008 | Narrowed | Existing paper, bounded claims, fixture artifacts and plotting inputs retained; open work is the verified bibliography, frozen statistical plan, complete claim matrix/manifests, offline table reproduction and threats-to-validity coverage. |

Issue #48 remains open until this PR merges; the PR uses `Closes #48` so closure
is tied to landing the corrected manifest rather than to an unmerged branch.

## Documentation scan

Current-state surfaces reviewed and reconciled:

- `README.md`
- `docs/CURRENT_STATUS.md`
- `docs/evaluation.md`
- `docs/research.md`
- `docs/roadmap/README.md`
- architecture, Factory, Studio, quickstart, research-paper, and swarm docs

Historical snapshots remain excluded exactly as declared in
`implementation-status.yaml`. Normative specifications are not interpreted as
current-state prose.

The stale-claim scanner now also detects `future work` phrasing when it is tied
to a family that the manifest marks implemented. A regression fixture proves
that this form fails. The existing deliberate stale-canonical-path fixture
continues to prove that `not_started` cannot coexist with a present canonical
implementation path.

## Verification evidence

```text
python3 scripts/status_check.py
status_check OK: 45 families, no stale doc claims, all referenced paths exist

python3 -m pytest -q tests/test_traceability.py
23 passed in 0.90s

python3 -m pytest -q
1323 passed, 53 skipped, 276 subtests passed; 10 host-capability failures
```

The ten broader-suite failures reproduce unchanged on pristine base
`50646c9`: nine require Bubblewrap/user-namespace execution that this runner
denies (`Operation not permitted`), and one cannot create an AF_UNIX socket
under the host policy. They are environment qualification failures, not
traceability regressions. The protected M4 test was not changed.

Generated status SHA-256:

```text
e5c1540ff4d32fd401f3e8192e040735f3607293e8666a71be5959586e0ca163
```

## Ambiguous or deliberately incomplete families

- `STUDIO`: real Factory/Station paths coexist with prototype frontend contracts.
- `M5`: implemented preview mechanics do not yet establish production or live-loop qualification.
- `GCP`: foundational control-plane types are not equivalent to end-to-end enforcement.
- `N9`: broad code coverage does not substitute for the required 30-day live soak.
- `PROD`, `MESH`, `MAI`, `APC`, `MEM`, `TRJ`, `NETOPS`, `SPEC-005`, and
  `SPEC-006` retain explicit residual requirements in manifest notes.
- `PQC`, `FMV`, `FED`, and `T10` remain `not_started`; their declared canonical
  paths are absent.
