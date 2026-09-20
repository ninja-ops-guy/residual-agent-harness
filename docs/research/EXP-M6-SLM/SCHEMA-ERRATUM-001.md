# SCHEMA-ERRATUM-001 — Nullable `timestamp` for `slm-observation-v0`

Lane: SLM-00 Corpus (Lane B)
Date: 2026-09-20
Status: PROPOSED — must be ratified as a versioned erratum per SLM-00-PROTOCOL split policy **before** corpus freeze; never applied silently or post-hoc after results.

## 1. Defect

`docs/research/EXP-M6-SLM/observation.schema.json` (blob `6e549b05e0fab3684d6ec7173985aa734e55ffca`) declares:

```json
"timestamp": {"type": "string", "format": "date-time"}
```

with `timestamp` in the top-level `required` list. Zero of the corpus-eligible structured sources inventoried in the SLM-PREFLIGHT-REPORT (OTX-003: 24 records; OBS-006: 22 events; DSM-004: ~60 journaled events; RUNTIME-005: 7 scenarios; VQ-002: ~260 records) carry a wall-clock timestamp. DSM-004 carries `time_ns: 0` (a synthetic clock — not wall-clock time). Strict conversion therefore fails for 100% of records, and fabricating timestamps is prohibited.

## 2. Erratum rule (explicit, deterministic)

**E1 (schema amendment).** The `timestamp` property is amended to:

```json
"timestamp": {"type": ["string", "null"], "format": "date-time"}
```

It remains in `required` (the key MUST be present), but its value MAY be `null` when no wall-clock time was recorded. This is the least-inventive option: the field's required presence is unchanged, its type is widened to admit null exactly as the schema already does for `provenance.mission_id`, `provenance.incident_id`, `provenance.generation`, and all `cost` subfields.

**E2 (provenance marker).** Every record emitted under this erratum with `timestamp: null` MUST carry, in `provenance` (additionalProperties: true permits this):

```json
"timestamp_erratum": "SCHEMA-ERRATUM-001"
```

so downstream consumers can mechanically identify erratum-affected records and exclude them from any latency/time-series analysis without ambiguity.

**E3 (no sentinel times).** No synthetic sentinel timestamp (epoch zero, freeze date, replay index encoded as time) may be written. `time_ns: 0` in DSM-004 journals is a synthetic clock value and MUST NOT be promoted into `timestamp`; DSM records carry `timestamp: null` under E1/E2.

**E4 (derived timing remains in `cost.latency_ms`).** Recorded durations (e.g. OTX `timing_breakdown`, OBS `worker_seconds`) are durations, not timestamps; they map to `cost.latency_ms` via deterministic ms conversion and are unaffected by this erratum.

## 3. Versioning

Records converted under this erratum keep `schema_version: "slm-observation-v0"` and are distinguished by the `provenance.timestamp_erratum` marker. If the schema document itself is edited, the edited schema constitutes `slm-observation-v0.1` and this erratum is its changelog entry; a corpus frozen under either form must declare which it used in its benchmark hash/manifest. Per protocol, this erratum is frozen before any train/validation/test split and before results are observed.

## 4. Consequences

- With E1+E2, strict schema-valid conversion with zero invented fields reaches: OTX 24/24, OBS-006 canonical-unit records, DSM-004 replay-class lineage records, RUNTIME-005 scenario records, VQ-002 sampled 50/50 (preflight §2.7).
- Without it, strict conversion is 0%.
- No record content other than `timestamp: null` + the provenance marker is affected.
