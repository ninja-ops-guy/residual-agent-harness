# RESIDUAL reviews — 2026-10-04

Completion batch against the reconciled master task list
(`RESIDUAL-task-completion-2026-10-04.zip`). All reviews are Rookie's;
approvals and authoring decisions remain with mike.

## Contents

- `INJ-C3-DECOMPOSITION-REVIEW.md` — adversarial review of the proposed
  INJ child-invariant decomposition (8 candidates) and eight §7
  dispositions. Verdict: QUALIFIED with targeted revisions. One
  must-fix before adoption (F1: FLW-006's falsifying test is
  unfalsifiable as written — split the residual-risk governance outcome
  from the test); F2–F6 are interface clarifications (EVD-007/ACC-003
  boundary, REA-004/ASM-003 actor interface, paraphrase-test ownership,
  QUAL-008 placement, RTE ownership on parser/executor tests).
- `SPEC-INJ-V12B-001-REVIEW.md` — review of the V12b observation-plan
  draft (V12b coordinator review). Verdict: QUALIFIED with targeted
  revisions. All five findings covered by the five questions; gaps are
  a per-cell per-principal-store design-implication capture field (G1),
  a registry-coverage completeness rule (G2), and two wording
  clarifications (G3, G4).
- `OC-R1-REVIEW-PACKET.md` — the 2026-10-03 SPEC-OC-CTRL-001 r1
  adversarial review (B1–B5 blockers, N1–N6 reconcile items), transcribed
  from the review record. Supplied because the 2026-10-04 work pack
  recorded E1/E2 as blocked on missing review materials.
- `SPEC-OC-CTRL-001-r1.pdf` — the r1 base spec (mike's file), included
  so the review packet and the r2 authoring have their base in one place.

## Completion note

- **C3:** review delivered (this package). Owner approval of the
  decomposition/dispositions still pending — the review informs it.
- **D1:** review delivered (this package). Owner review and
  finalization of the observation plan remain with mike.
- **F1:** independently verified from the repo checkout:
  `eaa1fff` ("Add INJ Class C cognitive battery v0.2.1 (post-v1,
  additive)") is on `review/auth-qualification-layer`, working tree
  clean. The 2026-10-04 work pack's "no Git checkout to verify" gap is
  closed.
- **C1/C2:** still blocked — confirmed the submission ZIP contains the
  r2.1 PDF and r0 Markdown lineage but no editable r2.1 Markdown
  source. No PDF reconstruction per the standing verification rule.
  The four-correction patch spec in the work pack is ready to apply
  the moment the source is supplied.
- **D2:** still needs mike's selection among (a)/(b)/(c); the
  composition probe remains mandatory before TF-INJ-001 closes.
- **E1:** r2 authoring still with mike; this package supplies the
  missing base materials (r1 + review). E2 delta review owed once r2
  exists.
- **A2–A4, B1:** unchanged — pending owner inputs / scheduled cycle.
