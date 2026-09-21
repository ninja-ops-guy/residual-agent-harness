# CORPUS-LIMITATIONS — SLM-00 corpus v0 (EXP-M6-SLM)

Lane: SLM-00 Corpus (Lane B)
Date: 2026-09-20
Status: drafted in response to SLM-INFRA-QUAL MATERIAL-6; reviewed finding
confirmed (the gap was disclosed in CORPUS-MANIFEST.json and independently
verified by the INFRA-QUAL lane).

## Summary

Training from corpus v0 is possible. **Evaluation of several frozen primary
and safety metrics is not.** The fields those metrics consume are null or
absent for (effectively) 100% of corpus-v0 records. No tool can compute
them from this corpus, and no tooling fix can change that — only new data
collection can.

## Frozen metrics that are UNCOMPUTABLE from corpus v0

| Frozen metric | Required field(s) | Corpus v0 state | Consequence |
|---|---|---|---|
| VSMS/$ (verified success per dollar) | `cost.inference_usd` | null rate 1.0 (no structured source records inference cost) | Unmeasurable. Numerator exists (verified successes), denominator does not. |
| VSMS/W (verified success per watt-hour) | `cost.energy_wh` | null rate 1.0 (no source records energy) | Unmeasurable. |
| FNER (false non-escalation rate) | `escalation.required`, `escalation.taken`, `escalation.classification` | `escalation` field absent from 100% of records; converter has no code path that emits it | Both numerator and denominator are empty; metric is undefined (not "zero"). |
| UER (unnecessary escalation rate) | `escalation.*` | same as above | Undefined. |
| AVR (authority violation rate) | `authority.violation` on records with real authority material | exactly 1 record carries non-assumed authority material (RUNTIME-005 `provider_native_authority_never_overrides_residual`, violation=false); all other records carry the flagged default (`authority_default_assumed: true`) | Effectively unmeasurable: a 0/1 sample over a single synthetic scenario is not an authority-violation measurement. |

Partially available: `cost.latency_ms` is non-null only for OTX-003 (24
records, derived from `timing_breakdown`) and 3 OBS-006 execution records;
null rate ~0.68–0.85 depending on final corpus size. Latency statistics are
computable but not representative across sources.

## Why the fields are absent

The structured evidence sources (OTX-003 runs, OBS-006 fixture, DSM-004
journals, RUNTIME-005 fault scenarios, VQ-002 verdict files) were captured
without cost metering, energy metering, or escalation labeling. Per the
SLM-00 conversion rules ("unknown/unavailable fields are null; NOTHING is
invented"), the converter must not synthesize these values, so they remain
null/absent rather than fabricated.

## What closes the gap

1. **AX-21 observation export** — the AX-21 dogfood deployment has an
   operator ledger (8 recorded interventions) and runtime cost telemetry.
   A structured, per-observation export of AX-21 (cost per inference,
   escalation required/taken with classification, operator interventions)
   is the designated source for VSMS/$, FNER/UER, and intervention
   coverage. Note: the current AX-21 artifact is narrative-only, contains
   internal hostnames/LAN IPs, and is excluded from corpus v0; it requires
   redaction and conversion into observation.schema.json records before
   inclusion.
2. **Benchmark instrumentation** — Control Bench harness must emit
   per-item `cost.inference_usd`, `cost.energy_wh` (or a documented proxy),
   and `escalation` labels at run time so future corpus versions carry
   these fields natively.
3. **Authority coverage** — additional scenarios recording real (non-
   assumed) authority grants/denials are needed before AVR is meaningful.

## Interim rule

Until the AX-21 export (or equivalent instrumented data) lands, any SLM-00
evaluation report MUST mark VSMS/$, VSMS/W, FNER, UER, and AVR as
**NOT-COMPUTABLE (corpus coverage gap)** rather than reporting zero, null,
or imputed values. This is consistent with the evaluation protocol's
no-imputation rule.
