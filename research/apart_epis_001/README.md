# APART-EPIS-001 draft pilot apparatus

Research preparation for [issue #510](https://github.com/ninja-ops-guy/residual-agent-harness/issues/510). P2 / POST-V1 / NONBLOCKING. All five owner gates remain pending. No participant recruitment, human collection, unblinding, protocol freeze, submission, or scientific claim is authorized by this package.

## Reproduce

Python 3.10+ standard library only; no installs, credentials, network, models, Station services, or release workers needed. From repository root:

```sh
python -m unittest discover -s research/apart_epis_001 -v
python research/apart_epis_001/pilot.py build /tmp/apart-draft-001
python research/apart_epis_001/pilot.py analyze /tmp/apart-draft-001
```

Use a new output directory each time. Existing runs/results are never overwritten. The build emits 14 cases, separate `custodian/truth.json`, `custodian/assignment.json`, `custodian/cases.json`, 56 static HTML presentations across four operator packets, a source/case/truth/assignment hash manifest, and 56 explicitly synthetic responses. Analysis emits deterministic `synthetic-analysis.json` with input hashes. Archive the entire output with the exact PR commit/tree, Python/platform identity and command transcript. Hashes establish byte identity, not origin authentication or semantic truth.

Only `operator/packet-N` is eligible for later participant delivery after approval. Do not serve the run root or repository. Custodian files, generator, tests, fixture responses and analysis must never be shipped with a participant packet. No JavaScript, tracking, external assets or network requests are used. Timing and burden collection are manual draft fields, not instrumented measurements.

**The public generator is a disclosed synthetic development corpus, not a secret human-study corpus.** Path separation prevents accidental page leakage; it is not encryption or blinding against someone who can inspect this repository. Before G2, a custodian must privately instantiate novel cases, independently validate their truth, commit their hashes, and restrict access. That private corpus is deliberately not published in this PR. Operator pages suppress condition/fault labels and the case-to-truth mapping, but participants can infer information availability; full treatment blinding is impossible.

The analyzer deliberately refuses non-synthetic responses. A separately reviewed, exact-revision human collection/unblinding implementation is required after G1/G2 and before G3/G4. Changing a `synthetic` Boolean is not permission to analyze humans.

## Components and lane reconciliation

This owner-requested draft fills interfaces without reassigning or declaring completion of Scout, Tester, Hermes, Wrench, Piston, STAR, or Challenger lanes. Existing lane ACK/capacity and unpublished work remain unknown. Reconcile their artifacts by exact revision before freeze. No swarm messages or dispatches were sent, no v1 owner reassigned, and no runtime/workflow/gate changed.

- `pilot.py`: matched constructed worlds, allowlisted A–D renderer, counterbalanced schedule, fixture generator, strict synthetic response validator and analysis.
- `test_pilot.py`: thirteen tests including hand-computed null, ideal-oracle software check, wrong verifiers, missing/aborted records, schema/hash rejection, rendering segregation and byte reproduction.
- `protocol.md`: proposed design, estimands, limits, sample/stopping rule and owner gates.
- `response.schema.json`: de-identified draft response contract (synthetic-only).
- `inventory.json`: observed source identities and inspection limitations.
- `RESULTS.md`: software findings only, negatives and unresolved review items.

No live RESIDUAL execution is represented by the constructed receipts. The fixture uses SHA-256 identifiers for synthetic sources/artifacts, not fabricated Git commits or signed receipts.

## Presentation-byte correction (PR #555 / finding #556)

`analyze(..., presentation_root=run_root)` now requires the generated HTML tree
and rehashes **all assigned presentations**, including missing/aborted responses,
before scoring. The CLI uses its run directory. The fixed mapping from
`SYN-00N` and assignment `order` to `operator/packet-N/XX.html` is checked;
missing files, symlink indirection, duplicate paths/tokens and byte mismatches
fail closed. Build writes UTF-8 bytes directly to avoid platform newline drift.
Response hashes must still equal the assignment hashes verified against bytes.

The analysis retains `presentation_verification`: scope, assignment digest,
and opaque presentation IDs, relative paths and actual SHA-256 digests. This
receipt adds no condition, case, fault or ground-truth fields to operator pages.
The overall analysis remains custodian-only. Verification reads files once;
keep the verified tree immutable and archive it with the receipt and source
revision. A local snapshot does not attest to historical browser delivery,
prevent subsequent changes, authenticate a maliciously rewritten manifest,
or prove semantic truth. Approved human delivery/capture must bind its own
served bytes and response receipts; human analysis remains disabled.

The original retained `synthetic_fixture` is historical evidence and omits HTML;
it must not be analyzed as if its bytes were available. Rebuild into a fresh
run directory using the commands above. Historical verification/results remain
unchanged; `integrity-verification.json` records the correction checks.
This reuses `RES-UP-RESEARCH-TEST-SUBJECT-PROVENANCE-001`. P2 / POST-V1 /
NONBLOCKING; G1–G5 owner approvals and v1 release state are unchanged.

## Missingness and cluster extension

See [analysis-extension.md](analysis-extension.md). `uncertainty.py` adds sharp
assigned-trial missing/aborted bounds and packet-stratified participant bootstrap
kernels (seed 510, 10,000 draws, 95% percentile intervals) for four bounded
outcomes and contrasts. The original singleton-per-packet fixture correctly
withholds intervals. `test_uncertainty.py` supplies separate dependent synthetic
multi-participant fixtures. No human ingestion/unblinding is enabled, no research
gate is approved, and no v1 release blocker is added.
