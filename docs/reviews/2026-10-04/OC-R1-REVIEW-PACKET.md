# SPEC-OC-CTRL-001 r1 — Adversarial Review Packet

**Reviewer:** Rookie. **Review date:** 2026-10-03.
**Source document:** `SPEC-OC-CTRL-001-r1.pdf` (60-section P1 v1 control-plane
integration spec).
**Purpose of this packet:** The 2026-10-04 work pack recorded E1/E2 as blocked
because "OC r1 and the B1–B5/N1–N6 review materials were not supplied" to that
workspace. This packet supplies the review side; the r1 PDF is mike's file.
**Verdict: NEEDS WORK** — architecture sound, five blockers require
section-level fixes before QUALIFIED.

## Architecture assessment (sound)

- Control-plane / execution-substrate split is right.
- Evidence-before-authority ordering is correct.
- A revision-history substantiation check verified every fix claimed in §0
  appears in the body (enrolled-key evidence authenticity and OCI-011;
  RESIDUAL-owned machine-checkable acceptance oracle and OCI-012 with
  mutation-controlled false-completion gate; RFC 8785 redact-then-digest
  configuration identity; signed runtime reconnect continuity; mandatory
  replay rejection with sequence/chain checks; EFFECTIVE configuration
  bounded by observed runtime validation; mandatory minimum evidence event
  set; conformance, receipt, cancellation, heartbeat, offline
  reconciliation, fault-injection, private-key, and exact-head/CAS-ledger
  closures).

## Blockers (section-level fixes required before QUALIFIED)

**B1 — No independent observation channel.** The compromised key-holding
plugin's false-acceptance-within-scope exposure is unstated in §53. Without
an observation channel independent of the plugin, a compromised plugin's
in-scope false acceptance is unobservable by construction.

**B2 — Enrollment without revocation.** No `runtime_id` retirement
mechanism. Enrollment without a runtime revocation/retirement path means a
compromised enrollment cannot be killed.

**B3 — Fault-injection hook's production status unspecified.** The spec
does not state whether the fault-injection hook exists in production
builds. A test hook with unspecified production status is a latent
privilege path.

**B4 — `CONFIG_DRIFT_DETECTED` consequence undefined.** The spec does not
define what `CONFIG_DRIFT_DETECTED` does to QUALIFIED status. An alert
with no consequence is telemetry, not a control.

**B5 — Acceptance oracle has no minimum criteria floor.** The oracle that
confers acceptance has no stated minimum bar — acceptance can be granted
on an empty or trivial evidence set.

## Reconcile-before-implementation items

- **N1** — SOURCE-digest check mechanism: how the digest check is performed.
- **N2** — `INTEGRITY_FAILURE` operational consequences + crash-recovery semantics.
- **N3** — Clock trust and skew bounds.
- **N4** — Key storage hardening requirements.
- **N5** — Weight of log-derived evidence (cf. TF-EVD-001: logs the agent can write are not evidence).
- **N6** — Advertised-vs-probed capability binding.

## Downstream use

- **OC r2 authoring (mike):** integrate TF-OC-001 (landed-digest == pinned-digest
  after every fetch/checkout/update; mismatch → `PIN_VERIFICATION_FAILURE`,
  suspend pin-bound qualification) and TF-RTE-002 (control-channel manifest
  states bind address + authentication; localhost is not identity;
  authenticate every command independently of network origin).
- **Delta review (Rookie, owed):** r2 vs r1 against B1–B5/N1–N6 above, once
  mike supplies r2.

---
*Transcribed 2026-10-04 from the 2026-10-03 review record (MEMORY.md).
No new findings added; section detail beyond the recorded verdict was not
retained in the record and is not reconstructed here.*
