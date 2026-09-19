# Security review — Aikido remediation pass

Date: 2026-09-19  
Scope: `main@e7b72ad18df5729f16d36771971c8a8828d71a10` plus the changes on `security/aikido-runtime-hardening`.

This is a source and trust-boundary review, not a claim that production qualification has passed. Merge/release status remains gated by exact-head CI and the repository's existing acceptance controls.

## Executive summary

This pass found three substantive code-level trust-boundary issues behind the scanner output and fixed them on the remediation branch:

1. third-party Python supplied to the Enterprise supply-chain sandbox was executed with `exec` in the host interpreter behind only a restricted-builtins layer;
2. enterprise integration connectors allowed an absolute request path to replace the configured origin while still attaching the connector bearer token;
3. SAML responses were parsed with the standard XML parser without explicit DTD/entity hardening or a document-size bound.

The pass also disables persisted `actions/checkout` credentials in workflows that did not need them and replaces several optimization-sensitive production `assert` statements with explicit fail-closed checks.

Several Aikido items are not code vulnerabilities on current `main`: the Docker image already drops to UID 10001, the reported Git hashes are provenance identifiers rather than credentials, browser service-worker `fetch` calls are not server-side request forgery, and the checked-in study `protocol.json` contains no credential-bearing keys.

## Confirmed findings and remediation

### SR-01 — Host-process execution of third-party Python

**Status:** fixed on remediation branch; exact-head qualification pending.

`residual/supplychain/sandbox.py` previously evaluated third-party module source in the parent Python process with a restricted builtins dictionary. Python language-level object restrictions are not an OS security boundary.

The new path requires Linux kernel isolation through `residual.sandbox.select_backend(require_kernel=True)`, rejects a root parent, denies network access, mounts only canonical allowlisted paths read-only, applies CPU/memory/PID/wall/output limits, and runs the dynamic Python source only in the isolated child interpreter. If kernel isolation is unavailable the operation fails closed.

Regression coverage exercises denied network egress, host-filesystem escape attempts, read-only mounts, traversal, the removed host callback filesystem shim, benign execution, and an isolated child process attempting to create a host marker.

### SR-02 — Integration connector origin override / credential-forwarding SSRF

**Status:** fixed on remediation branch; exact-head qualification pending.

`IntegrationConnector.call()` previously accepted an absolute `path` and used it as the request URL while still attaching the connector's bearer token. A caller able to influence that value could pivot a credentialed connector to another origin.

The connector now validates its configured base URL, accepts only origin-relative endpoint paths, rejects scheme/netloc overrides, network-path references, backslashes and control characters, disables ambient proxy routing in the real urllib transport, and refuses HTTP redirects. Regression tests cover loopback, link-local-style metadata targets, alternate origins, malformed base URLs and transport non-invocation on rejected input.

### SR-03 — SAML XML parser hardening

**Status:** fixed on remediation branch; exact-head qualification pending.

SAML input is authentication data and must be treated as untrusted XML. Parsing now uses `defusedxml`, explicitly forbids DTDs, entities and external references, caps the document at 1 MiB, and normalizes unsafe/malformed XML to `ContractError`. Tests cover an external-entity/DTD payload and oversized input.

Aikido PR #321 had the correct high-level direction but was not merge-ready: it introduced an undeclared runtime dependency and did not include the size/failure-normalization regression coverage carried here.

### SR-04 — Persisted GitHub Actions checkout credentials

**Status:** fixed on remediation branch.

All workflows found using `actions/checkout@v4` without an explicit opt-out were changed to `persist-credentials: false`. Workflows that already used the hardening were left unchanged. Jobs that need authenticated GitHub API operations continue to use their explicit scoped token surfaces rather than a credential stored in the checkout configuration.

### SR-05 — Optimization-sensitive production assertions

**Status:** partially fixed on remediation branch.

Production assertions used as runtime integrity checks were replaced with explicit exceptions in the non-Factory code touched by this pass, including sandbox startup state, telemetry registry consistency, compliance wiring, DSM recovery invariants and marketplace entry-point validation.

The protected Factory trust-boundary file `residual/factory/termination_provenance.py` was deliberately restored byte-for-byte to the current ownership baseline. Any change there must follow the Factory ownership/baseline qualification procedure rather than being smuggled into a scanner-cleanup PR.

## Aikido findings classified as stale, non-applicable, or requiring external action

### Docker runs as root

Current `Dockerfile` creates user `station` with UID 10001, owns the writable application/data paths accordingly, and executes `USER station` before the entrypoint. Treat the scanner item as stale until a fresh image/rescan proves otherwise.

### File-inclusion report / Aikido PR #322

PR #322's proposed `if ".." in path` filter is not a security boundary. It permits arbitrary absolute paths and symlink escapes while also rejecting benign filenames. It has been reviewed with changes requested.

The workbench source reader inspected in this pass already anchors reads under a resolved root, rejects absolute paths and backslashes, walks path components with symlink rejection, checks the final resolved path remains beneath the root, and enforces file/size constraints. The generic OTX `ObservationLog.read/write` helpers are currently used as operator/test persistence primitives rather than an untrusted remote file-read surface. Aikido's remaining file-inclusion subissues should still be evaluated call-site-by-call-site when their exact list is available; a blanket substring patch is not accepted evidence.

### Service-worker “SSRF”

`site/coi-serviceworker.js` and the WebVM retry fragment issue browser `fetch` calls on behalf of browser requests. They are client-side service-worker code, not a server capable of reaching private infrastructure on an attacker's behalf. The provider bypass is additionally same-origin and path-scoped. This scanner category is not applicable as SSRF.

### Maintainer-approval “SSRF”

`scripts/check_maintainer_approval.py` builds GitHub API paths under the literal `https://api.github.com/` authority. Repository and PR identifiers are inserted into the path, not the URL authority. It does not expose a user-controlled request destination. This item should be classified as not exploitable in the current call graph.

### Runtime installer request

The Ollama runtime downloader takes its URL from the checked-in platform manifest and verifies the full downloaded archive against the checked-in SHA-256 before extraction. The URL is not supplied by an HTTP client or model output. This is a pinned supply-chain download rather than an SSRF surface.

### Exposed hashes in `factory_ownership_baseline.json`

The reported 40-character hexadecimal values are Git object/blob identifiers used for exact-content ownership/provenance. They are not API keys, bearer tokens or passwords and should remain in the repository. Removing them would weaken the ownership mechanism.

### `docs/cic-qa/protocol.json` secret alert

A structured inspection of the current file found no credential-bearing keys. The only key matching a broad token heuristic is the numeric `max_output_tokens` limit. Current study configuration also explicitly rejects fields named API key, token, secret, password, authorization or headers.

### Historical FreeLLMAPI secret alert

The filename shown by Aikido is not present on current `main`. Historical-secret findings cannot be closed solely by deleting a file: the exact detected value/provider must be reviewed in Aikido. If it is a real credential, revoke/rotate it even if the file is gone. Do not rewrite repository history merely to silence the scanner until credential validity and downstream provenance impact are established.

### GitHub organization IP allow list

This is repository/account governance, not a source-code defect. Enabling an organization allow list is appropriate only if the account/plan supports it and legitimate maintainers/runners have stable approved egress. It must not be enabled blindly because it can lock out GitHub-hosted automation and roaming maintainers.

### CSP / clickjacking on GitHub Pages

Tracked separately in PR #320. GitHub Pages does not provide repository-controlled arbitrary response headers. The security-qualified production origin should be a deployment layer that can emit the actual CSP and `X-Frame-Options` response headers; the repository-level HTML meta policy is only a browser-side fallback.

## Additional review findings

### AR-01 — Enterprise IAM uses custom cryptographic protocol code

**Risk:** material if the Enterprise IAM module is used as a production authentication boundary.

`residual/iam/crypto.py` implements RSA PKCS#1 v1.5 and JWT/JWS directly in Python, and the SAML module documents a simplified detached-signature convention rather than full XML-DSig. The implementation does reject `alg=none`, checks issuer/audience/time claims, and uses constant-time HMAC comparison, but custom cryptographic protocol implementations carry interoperability and side-channel/canonicalization risk.

**Recommendation:** before advertising the IAM layer as a production identity boundary, replace the custom RSA/JWT/SAML signature path with a maintained cryptographic/JWT/SAML implementation, enforce modern key-size policy, and add signature-wrapping/key-confusion/replay corpora. Until then, keep claims bounded to the tested implementation.

### AR-02 — Remote exposure of the local Command Station needs an upstream access boundary

**Risk:** conditional.

The Station is loopback-first, validates Host/Origin/Sec-Fetch-Site, uses session/worker tokens, sets CSP/no-store/nosniff, and documents TLS/SSH-tunnel use for remote workers. However `/api/bootstrap` intentionally returns the local UI session token after Host checks so the local browser can initialize. If a reverse proxy exposes the Station to an untrusted network without an authentication layer, network clients reaching the allowed Host could bootstrap a session.

**Recommendation:** keep the Station loopback-only by default. For remote web access, require an authenticated reverse proxy/private network boundary rather than relying on the bootstrap token as perimeter authentication.

### AR-03 — Historical secrets require provider-side resolution, not source deletion alone

A source scan can establish that a credential is absent from current `main`; it cannot prove a historical credential was harmless or revoked. Historical findings should be resolved only after classifying the detected token type and, when real, rotating/revoking it at the provider.

## Positive controls observed

- Docker runtime drops privileges to a dedicated UID.
- Station root directory is set to mode 0700 and session/worker tokens are generated with `secrets.token_urlsafe`.
- Station HTTP responses already emit CSP, `frame-ancestors 'none'`, `nosniff`, no-referrer and no-store.
- Provider configuration rejects embedded URL credentials and insecure non-loopback HTTP.
- Factory worker dynamic execution is preceded by OS isolation/seccomp/resource controls; its `exec` is not equivalent to the removed host-process supply-chain path.
- Factory artifact writes use directory-relative/no-follow patterns and protected paths are governed by an ownership baseline.
- Runtime archive downloads are checksum pinned and ZIP extraction checks destination containment.
- The repository's SecOps module already scans candidate code for private-key blocks and hardcoded credential patterns before staging.
- SQL paths inspected in Station/Factory use parameterized statements for attacker-controlled values.

## Release decision for this review

Do not treat this document or scanner status as release acceptance. The remediation branch must pass exact-head repository tests and security regression tests. PR #320 must separately qualify the real deployed response headers on the production origin. Historical secret findings must be resolved in the provider/Aikido workflow, not by assuming that current-code absence means revocation.
