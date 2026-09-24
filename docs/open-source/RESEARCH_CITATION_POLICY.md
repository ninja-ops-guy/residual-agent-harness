# Research citation and archival policy

RESIDUAL research should remain citable even as the repository evolves rapidly.

## Software citation

Use `CITATION.cff` and cite the exact release tag or commit SHA used.

## Experimental citation

A research result should reference the smallest stable artifact set that makes the claim reproducible:

- experiment/protocol identifier;
- exact code revision;
- benchmark/data manifest and digest;
- model/runtime configuration;
- verifier/evaluation version;
- evidence bundle or receipt digest;
- publication/preprint/DOI when available.

## Release policy

For research-significant milestones:

1. create an immutable version tag;
2. publish release notes describing the research scope and non-claims;
3. attach or link frozen manifests/evidence;
4. preserve cryptographic digests for the release artifact and key evidence;
5. archive the release and associated research material with a DOI-capable archival service when practical;
6. add the DOI to citation metadata without rewriting historical artifacts.

## Authorship

Human authorship should reflect substantive intellectual or research contribution. AI systems used for drafting, implementation, analysis, or review are tools and should be disclosed when materially relevant to methodology, but are not listed as human authors.

## Negative results

Failed trials, contradictory evidence, and null results remain part of the research record. Later success does not erase earlier failure.

## Attribution language

Third parties may accurately describe work as based on, derived from, reproducing, or evaluating RESIDUAL when supported by evidence. This project does not require claims of endorsement.

## Future identifiers

ORCID, DOI, archival accession, or formal publication identifiers should be added only when actually obtained. Placeholder identifiers must not be invented.
