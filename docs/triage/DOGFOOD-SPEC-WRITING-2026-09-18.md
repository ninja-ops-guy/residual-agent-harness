# Dogfood record — RESIDUAL writes one spec (2026-09-18)

**Verdict: WORKED (mission machinery) / BLOCKED (real model authorship).**

## What was done

1. Cloned the repository anonymously at main `4608afabf5de4c87d77aaf149dfc12538d364f43`.
2. Installed into a fresh venv: `pip install '.[factory]'` (Python 3.12) — succeeded; `residual --help` works.
3. Used the installed RESIDUAL Station (programmatic `residual.station.service.Station` API, the same path the container smoke test uses) to run one real mission whose single task was to **write one spec from the Wave A pack**: `docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md` (the control-plane durable-ledger spec derived from A1).
4. Recorded both a negative control and the substituted-provider run.

## Attempt A — real local model route, no provider configured

- `run_one` on the `local` route with no configured provider → task `SPEC-1` transitioned to `repair_required` in 0.068s; no candidate was fabricated, no silent fallback occurred.
- This is the honest BLOCKED/UNKNOWN evidence for actual model authorship: **no model credentials exist in this environment, so RESIDUAL did not author the spec text with a model.** The historical position stands: real-provider authorship remains unqualified until a fresh real-provider run on a frozen RC succeeds.

## Attempt B — scripted local provider, real mission machinery

The local provider was a scripted `openai_compatible` endpoint returning the spec bytes (fixture substitution, explicitly declared — this qualifies the *machinery*, not model authorship):

- triage → claim → candidate → deterministic checks (`exists`/`contains` ×4 incl. `exactly-one-terminal`, `CAS`, `commit-before-ack`) → `review_ready` → scripted review `approved` → **integrated** (`5af5675aec3700190eace07e1dda778c58158d1d` on top of the source repo's init commit) → release export completed.
- Verification receipt hash: `dc5ffb9ce3ee4296c562d57cde3f114969b96a8c37fec4518c15dc45d30a9ded`
- Release artifact: `p-c6b815ac1ab8:4adf010791fa548d8c6c2069cfaf333d6b061f06e4989530d3329f93d12e191d` (3904 bytes, sha256 `4adf0107…`)
- Integrated spec file sha256: `0709034c46c28a7d32990d984d23f815aa3f7a544a75b9451bd865cce5bc8825` (retained as `produced-spec.md` alongside this record)
- Observation export sha256: `efc88f0735b07310f083dfe3d0d9f40dada165612a2bb32589fd2ceec39f6481`
- Metrics: 3 model calls, 17 events, 40 reported tokens.

## First-run friction observed (honest failure record)

1. `Station.create()` rejected an empty source: `ContractError: Choose an existing local Git repository path` — a mission requires a pre-existing local git repo as the project workspace. Fail-closed and clear, but a first-run UX note for the quickstart (P2-7).
2. First Attempt B run failed verification: `check-4: Required text was not found` — the mission required the literal `commit-before-ack` but the source document capitalized it (`Commit-before-ack`). The check runner did exactly what it should (failed the candidate, transition to `repair_required`); the mission was repaired by adding a normative appendix containing the required literal strings and re-run successfully. This is retained as evidence that content checks have teeth.
3. Metrics anomaly: `unreported_calls: 1` — one of three provider calls did not record usage. Worth a follow-up look against the observability SLO work (P1-O5); recorded, not explained.

## Claims and non-claims

- CLAIM: on this exact head (`4608afab`), a fresh install can run a complete Station mission lifecycle (create → triage → claim → candidate → verification → review → integration → release export) with retained receipts/artifacts, offline.
- CLAIM: verification checks fail closed on missing required content; repair re-entry works.
- NON-CLAIM: RESIDUAL did not author the spec via a model. Attempt B's provider was scripted; no model-quality, authorship, or production-reliability claim is made.
- NON-CLAIM: this is not the P0-8 real-provider E2E gate and does not change the historical Puter FAIL/BLOCKED status.

## Reproduction

`runner.py` (retained alongside) contains the exact mission spec, provider stub, and evidence capture. Requires `pip install '.[factory]'` and a local git repo as mission source.
