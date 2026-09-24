# GitHub Secure Open Source Fund — readiness note

**Status:** DO NOT SUBMIT YET  
**Official program:** https://github.com/open-source/github-secure-open-source-fund

## Why this is relevant

The program funds security improvements for open-source projects and supports individual maintainers/small teams. Current published benefits include:

- $10,000 per selected project;
- a 3-week security education program;
- GitHub Security Lab access;
- security community and incident-management support;
- $10,000 in Azure credits, with some eligible projects potentially able to access larger Microsoft for Startups infrastructure credits.

Applications are rolling.

## Current fit

RESIDUAL has strong security/reliability substance:

- protected branch and qualification gates;
- evidence/receipt integrity mechanisms;
- security and provenance policy;
- adversarial testing and negative-result retention;
- explicit authority and commercial/open-source boundary checks;
- immutable-source export hardening and isolated Open Core qualification.

## Current eligibility blocker

GitHub explicitly requires an **open source first project with demonstrated community traction and adoption**, plus a clear open-source license and governance structure.

Engineering activity is not adoption. The repository should not represent PR count, test count, AI-agent activity, or internal swarm usage as community traction.

Before applying, retain genuine external evidence such as one or more of:

- external human contributors;
- downstream users/projects;
- independent reproductions;
- stars/forks that reflect real interest;
- package/download usage;
- external citations/tutorials/issues;
- an organization independently using or evaluating the Open Core.

## Minimum application gate

1. Merge an explicitly reviewed, legally acceptable Open Core boundary.
2. Publish an independently usable Open Core release/package.
3. Obtain at least some verifiable external adoption/usage.
4. Retain governance/security docs on the released revision.
5. Prepare a security improvement plan suitable for the program's required milestones.
6. Confirm maintainer availability for the 3-week program and later check-ins.
7. Apply without inflating adoption claims.

## Proposed security milestones if eligible later

- threat-model the public verification kernel;
- harden provenance/evidence parsing and serialization;
- dependency/SBOM and release-signing controls;
- fuzz/adversarial tests for receipts, manifests and trust-boundary parsing;
- reproducible release/export qualification;
- secret-scanning and supply-chain policy;
- external security review/challenge;
- incident-response playbook and disclosure workflow.

## Funding boundary

If selected, program funds should support the released Open Core security work and its public security deliverables, not reserved enterprise/commercial feature development unless the award terms explicitly permit it.
