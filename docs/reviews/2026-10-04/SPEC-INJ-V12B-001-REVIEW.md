# D1 Review — SPEC-INJ-V12B-001 observation-plan draft

**Reviewer:** Rookie (V12b workstream coordinator). **Date:** 2026-10-04.
**Source:** `RESIDUAL-follow-up-workpack-2026-10-03.md` (D1/D3 sections).
**Verdict: QUALIFIED with targeted revisions.** All five findings are
covered by the five questions; the procedure's sandbox, mutation-check,
and per-subcase reporting rules are right. The gaps below are
completeness-criterion and capture-field additions, not structural.
Owner review and finalization remain with mike.

## Coverage check (finding → question)

| Finding | Question | Covered |
|---|---|---|
| TF-INJ-001 authorized-tool/out-of-scope-args | Q1 direct argument scope | Yes |
| TF-INJ-004(b) wrapper-command path scope | Q2 wrapper-command scope | Yes |
| TF-RTE-001 parse-execute coherence | Q3 quoting/redirects/substitution | Yes |
| TF-INJ-002 repo-controlled preconditions | Q4 binary/config/hook enumeration + sink plant | Yes |
| TF-INJ-005 composition | Q5 composition probe | Yes |

## Findings

**G1 — Missing capture field: design implications for per-principal stores.**
TF-INJ-004's input (a) is that per-principal stores are "the working
answer shape for V12b" — a *design* input, not just an observation
target. The plan observes the v1 gateway (which has no per-principal
stores) but never says how observations feed the design. Add a per-cell
capture field: "design implication for per-principal stores" (e.g.,
"this tool's scope granularity suggests a per-principal store boundary
at X"). Without it, the observation fulfills the letter of TF-INJ-004
and loses its design value.

**G2 — No registry-coverage completeness rule.**
The plan's stated purpose is to "replace the V12b assertion with an
observed result." That requires a completeness criterion the draft does
not state: *every* registered/authorized tool must be observed through
Q1, or the scoping (which tools, why the subset) must be explicit with
rationale. "Pin tool registry" is listed in the procedure, but pinning
is not covering. An observation plan that retires an "unverified
assertion" without a coverage rule can silently re-create the same
assertion one level down ("we observed the tools we looked at").

**G3 — Q5's "approved external destination" needs the sandbox clarification.**
The procedure correctly requires "no network egress." Q5 grants "a write
to an approved external destination" — in a no-egress sandbox that
destination MUST be a simulated/observed sink, stated explicitly.
Otherwise a future reader will either violate the sandbox rule or
misread the probe as requiring real external infrastructure.

**G4 — Q4 wording (minor).** "Plant a `core.fsmonitor`-class sink in a
read-only operation on an untrusted clone" — the operation is a *read*;
the sink *executes on read*. Reword to "plant the sink in an untrusted
clone, then perform the harness's normal read-for-context path" to avoid
implying the sink is planted "in" an operation.

**Positive — mutation-verified detectors.** The requirement to repeat
each behavior-changing test with a benign control *and* a planted
mutation "to prove the detector can fail" is the strongest methodology
in the draft. Keep it; consider making it the workstream-wide standard.

**Positive — D2 gate placement.** The composition decision gate matches
the register's forcing function ((a)/(b)/(c), silence not an outcome),
and the owner's (a)-first recommendation is consistent with the
TF-INJ-005 composition memo's (a)+(c) hybrid. No conflict.

**Positive — per-subcase reporting.** "Unlisted tool denied does not
close authorized-tool/out-of-scope-arguments" is exactly the
non-inference discipline the plan needs. This sentence should survive
finalization verbatim.

## Adoption checklist

- [ ] G1: add per-cell "design implication for per-principal stores" capture.
- [ ] G2: state the registry-coverage completeness rule (every registered tool, or explicit scoping with rationale).
- [ ] G3: clarify Q5's external destination is a simulated sink under no-egress.
- [ ] G4: reword Q4's sink-planting description.
