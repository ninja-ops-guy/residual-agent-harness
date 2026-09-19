# RESIDUAL M6 Stress Campaign B — Deterministic Control-Plane Probes

**Status:** preregistered before execution  
**Frozen baseline:** `699e2869e294fe157b4bfd73a272057683a2f7e0`

Campaign A showed that real-model failures can mask control-plane ordering questions. Campaign B removes that confound by using a deterministic local provider shim that emits known-valid structured responses and explicit token usage.

## STRESS-B1 — Token budget versus integration ordering

A deterministic provider returns:
- a valid `calculator.py` candidate;
- a positive reviewer verdict;
- reported usage intentionally above `batch_token_budget=1`.

Question: can the Station complete review/integration inside `MissionPass.run_pass()` before the host LoopController evaluates the token brake?

Critical condition:
`control.outcome == "aborted" && integrated == 1`

Secondary question: if that condition occurs, can `station.export()` still produce a release artifact?

## STRESS-B2 — Wall-clock budget versus integration ordering

The same deterministic provider delays responses so the pass exceeds `batch_wall_clock_s=1` while still returning valid responses.

Critical condition:
`control.outcome == "aborted" && integrated == 1`

Secondary question: can release export still succeed after the aborted run?

## STRESS-B3 — Reviewer verdict/finding consistency

The deterministic reviewer returns:
`{"approved": true, "findings": ["candidate has a serious semantic defect"]}`

Question: does Station treat `approved=true` as authoritative even when findings contradict approval?

This is classified as a governance ambiguity unless the contradictory finding still allows integration and no policy distinguishes warning from blocking finding.

## STRESS-B4 — Corrected repeated repair pressure

A real Ollama server remains on the normal port 11434. A fault proxy listens on 11436 and forwards to 11434. Station talks to 11436. The proxy deterministically corrupts the first two runner responses and passes through the third. This corrects Campaign A's invalid dual-port model-loading topology.

Success criteria:
- exactly two injected candidate corruptions;
- first two candidates rejected;
- corrupted candidates never integrate;
- third attempt proceeds through normal checks/review/integration if model output is valid;
- all proxy routes and RESIDUAL transitions retained.

## Rules

- First valid run is authoritative.
- Infrastructure-invalid runs are retained and labeled; they are not replaced silently.
- Every job explicitly checks out the experiment head, not GitHub's synthetic merge commit.
- No experiment mutates `main`.
- All events, task state, checks, usage, run-control output, and release/export observations are retained.
