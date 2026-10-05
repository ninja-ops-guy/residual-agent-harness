# C3 Review — Proposed INJ child-invariant decomposition + §7 dispositions

**Reviewer:** Rookie. **Date:** 2026-10-04. **Source:** `RESIDUAL-follow-up-workpack-2026-10-03.md`
(C3 sections) from the 2026-10-04 work pack.
**Verdict: QUALIFIED with targeted revisions.** The decomposition is sound —
eight testably distinct properties, and FLW-006 correctly names the
TF-INJ-005 category instead of burying it. One finding (F1) must be fixed
before adoption; F2–F6 are interface clarifications. None is architectural.

## Findings on the candidate invariants

**F1 — FLW-006's falsifying test is unfalsifiable as written (fix before adoption).**
The proposed test: "assert a flow decision or explicitly bound residual-risk
outcome." The second disjunct lets paperwork satisfy an invariant test — any
flow, mediated or not, passes if someone wrote it down. Split the two:
the invariant's falsifying test MUST be "unmediated, unrecorded flow =
FAIL," and residual-risk recording is a *governance outcome* evaluated by
a separate process (the D2 gate), not a test pass. As written, the
invariant cannot fail, which means it cannot qualify anything.

**F2 — EVD-007 overlaps ACC-003; state the boundary explicitly.**
"Only typed authority-bearing fields can authorize" is close to ACC-003's
"the verifier produces proof but never converts to acceptance." The real
distinction: ACC-003 owns the verification→admission boundary; EVD-007
generalizes the principle to *all* prose-shaped content (verifier prose,
model output, logs) regardless of emitter. That generalization is worth
having — it is the V01-adjacent principle — but the decomposition must say
so explicitly, or qualification will double-count the same test under two
invariants.

**F3 — REA-004 vs ASM-003: are the "authorized actors" the same?**
REA-004's "authorized reasoning actor" creates instructions; ASM-003's
"authorized actor" is the only other party allowed in the instruction
channel. If they are the same actor, say so — the two invariants are then
two halves of one property (provenance of the channel + separation of the
reasoning that feeds it), and their tests must be designed jointly. If they
are different, define what distinguishes a "reasoning actor" from any
authorized actor. Currently the same test (route external bytes through an
assembly point) could be claimed under both.

**F4 — The paraphrase case sits at a three-invariant junction.**
ING-001 (typing at ingress), CHN-002 (type preservation through
transforms), and REA-004 (summarizing ≠ instructing) all touch
paraphrase/summary. The work pack's disposition 4 correctly makes this an
auditable process criterion, but the decomposition should name which
invariant owns the paraphrase test: recommend CHN-002 owns "output stays
UNTRUSTED_DATA," REA-004 owns "no new instruction was issued," with the
two tests run as a pair on the same trial. Otherwise one trial gets
triple-counted across three invariants.

**F5 — QUAL-008 is methodological, not a threat property.**
Claim-binding (prompt-freeze discipline) applies to AUTH qualification
equally. As an INJ child it will read as scope filler. Recommend promoting
it to a family-level methodology invariant, or keeping it here with an
explicit note that it is cross-cutting methodology, not an INJ threat
property.

**F6 — ACT-005's test list includes an RTE property.**
"Parser/executor divergence" is TF-RTE-001's parse-execute coherence —
an RTE-LOCAL property. Keeping the test is fine (defense in depth), but
name the ownership: the INJ invariant asserts *authorization over the
exact operation and arguments*; the coherence of what was parsed vs what
executed belongs to RTE. Scope bleed between families now becomes
jurisdiction disputes later.

**Positive — ASM-003 is the right home for V17.** The ten production
system-role assembly points from the §2.0 survey are exactly ASM-003's
test surface ("route external bytes through each instruction assembly
point"). Make the link explicit: ASM-003's qualification *is* the V17
re-verification requirement, not a separate activity.

## Findings on the §7 dispositions

**D1 — Disposition 1 answers an instance, not the question.**
Adopting the forged-receipt and terminal-escape tests as Class R evidence
is fine and additive, but the open question was general: what do we do
with rejection paths that map to no invariant? Restate the standing rule
as the disposition: flag UNMAPPED, never force-fit; a genuine gap is a
CTR-004 spec amendment, not a quiet edit. The two tests are then *examples
under* the rule, not the rule.

**D7 — Disposition 7 overclaims against a compromised actor.**
"It cannot silently bypass the conversion record" — if the reasoning
actor is compromised, the record is written by the compromised actor.
The honest guarantee is *detectability/auditability*: the conversion
record exists, is bound to the actor's grant, and a compromised actor's
misuse is visible in the record to an auditor. Restate in those terms;
"cannot silently bypass" promises prevention the design does not deliver.

**Agree:** D2 (no production cognitive-telemetry event — avoids both the
attacker-facing oracle and false confidence in model self-detection), D3
(attest at the trusted local ingress; provider label descriptive only),
D4 (paraphrase as auditable process criterion — the only measurable form),
D5 (linked provenance attestation with own digest — avoids AUTH schema
churn), D6 (generic `IMPLICIT_AUTHORITY_COERCION` first, child codes only
on demonstrated operator need), D8 (separate sequence/composition test
class before broad claims — correctly notes D2's selection as a
dependency).

## Adoption checklist

- [ ] F1: split FLW-006's falsifying test from the residual-risk governance outcome.
- [ ] F2: write the EVD-007/ACC-003 boundary note.
- [ ] F3: define the REA-004/ASM-003 actor interface.
- [ ] F4: assign paraphrase-test ownership (CHN-002 + REA-004 paired).
- [ ] F5: decide QUAL-008's placement (family-level vs INJ child).
- [ ] F6: name RTE ownership on the parser/executor test.
- [ ] D1: restate the general UNMAPPED rule above the two example tests.
- [ ] D7: restate as detectability/auditability guarantee.
- [ ] Link ASM-003's qualification to the V17 re-verification requirement.
