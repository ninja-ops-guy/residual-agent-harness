# Evidence authority adversarial qualification

This synthetic-only extension to PR #415 attacks the manifest/cardinality
invariant without touching either existing seal or authoritative evidence.

## Result matrix

| Attack | Current verifier result | Qualification disposition |
|---|---|---|
| added manifest entry | count recomputed | covered |
| removed manifest entry | count recomputed | covered |
| duplicate path | rejected | covered |
| malformed line | rejected | covered |
| absolute path | rejected | covered |
| traversal path | rejected | covered |
| wrong digest | rejected | covered |
| missing referenced file | rejected | covered |
| stale derived count | rejected | covered |
| extra unmanifested file | accepted/out of scope | open policy requirement |
| hashed but semantically false metadata | accepted/out of scope | open semantic-verifier requirement |
| derived artifact trusting derived artifact | accepted/out of scope | open provenance requirement |

The last three are intentionally passing characterization tests, not claims
that the behavior is sufficient. Hash validity proves byte identity, not claim
truth or provenance authority.

## Governing principle

**Derived evidence metadata must never become evidence authority when the
claim can be recomputed from an authoritative artifact.**

Consequently, a seal verifier must obtain cardinality, gate counts, candidate
identity, evidence digests, and dispositions from their named authoritative
sources. A derived document may cache those values only when the verifier
recomputes and compares them. Derived-to-derived trust chains cannot substitute
for that source traversal.

## Proposed qualification requirements

- `EG-G01 MANIFEST_GRAMMAR`: reject ambiguous, duplicate, absolute, traversal,
  empty, or malformed entries before reading targets.
- `EG-G02 BYTE_CLOSURE`: independently hash every referenced regular file and,
  when a package declares closed-world semantics, reject extra files according
  to an explicit allowlist (for example the manifest itself).
- `EG-G03 DIRECT_DERIVATION`: recompute every recomputable seal field from the
  authoritative artifact; do not accept an expected count/value as input.
- `EG-G04 SEMANTIC_BINDING`: independently bind candidate HEAD/tree, complete
  gate ID/status set, and final disposition to their authoritative records.
- `EG-G05 PROVENANCE_DAG`: label artifacts authoritative or derived, reject
  cycles, and require every derived claim to terminate at a named authoritative
  source rather than another summary.
- `EG-G06 INDEPENDENT_IMPLEMENTATION`: final acceptance uses a frozen verifier
  whose parser/derivation path is independent from the generator.
- `EG-G07 FAIL_CLOSED`: missing, unreadable, unrecognized, skipped, or
  semantically inconsistent evidence can never produce `PASS`.

Evidence source: PR #415 and synthetic fixtures only. Candidate referenced:
`8701367db6d3202f24b3eb9f4696b0cadf657985`. Candidate modified: no. Tests:
adversarial manifest unit tests. Blockers/pre-canary: broader semantic and
provenance verification remains an open requirement for future seals; Seal v2
itself was independently checksum-verified and was not modified. Production
findings: none asserted. Research finding: hash closure and semantic authority
are separate claims. Canary execution status: **NOT EXECUTED**.
