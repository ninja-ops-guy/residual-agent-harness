# Open-source funding readiness

**Status: CANDIDATE / NOT YET CERTIFIED**

The goal is to make funding claims narrow, reproducible, and consistent with the commercial boundary.

## Technical gates

- [x] Machine-readable include/exclude boundary exists.
- [x] Open-core archive selection is pinned to an immutable Git snapshot.
- [x] Export rejects untracked/staged working-tree bytes, unsafe paths, symlinks, submodules, reserved-path leakage and overwrite.
- [x] Import-closure CI exists to detect local dependencies crossing outside the proposed license scope.
- [ ] Candidate minimal manifest passes import closure at its exact head.
- [ ] Extracted source archive passes isolated smoke imports at its exact head.
- [ ] Full current-main reconciliation completed.
- [ ] Required protected-branch qualification completed at the exact candidate head.

## Legal/provenance gates

- [x] Apache-2.0 text is retained in-repo.
- [x] Citation and project-origin records exist.
- [x] CONTRIBUTING/security/provenance policies exist.
- [ ] Historical public license activity reviewed for actual legal effect.
- [ ] Employment/invention-assignment obligations reviewed.
- [ ] Contributor copyright/provenance reviewed; DCO is not treated as an assignment.
- [ ] Transitive dependency/SBOM review completed before packaged release.

## Funding claims allowed after the technical gates pass

Describe RESIDUAL Open Core as the project's **open verification and research kernel**. Do not describe the complete RESIDUAL runtime, Factory, Studio, enterprise product, or reserved implementation as Apache-2.0.

Funding should be scoped to open research/kernel maintenance, reproducible evaluation, model comparisons, benchmark execution, qualification and published research artifacts unless the applicable agreement explicitly permits broader use.

## Adoption claims

Use external adoption evidence separately from engineering velocity. PR counts, test counts and agent activity are not substitutes for users, downstream projects, contributors, stars, forks or citations.
