# SNYK-R4-01 independent evidence unit

- DIRECT_REQUEST_DESTINATION_CONTROL: CONSTRAINED. Gateway `_route` parses the request JSON and passes it as `_json`'s body. Its URL is operator-configured `FREELLM` plus the literal `/v1/chat/completions`; request host, port, path, URL fields and message contents do not select authority. Session setup uses operator configuration and fixed Tailscale URLs. The soak CLI parses the port as an integer and constructs `http://127.0.0.1:{port}`; station-generated IDs enter paths after a fixed authority.
- REDIRECT_AUTHORITY_DELEGATION_PRE_FIX: EXPLOITABLE when the configured upstream (gateway) or local station (qualification) supplies a redirect. Default urllib handling followed HTTP/HTTPS/FTP destinations outside the original authority. This is an upstream-response trust-boundary defect, not demonstrated direct remote request-body SSRF. The qualification consequence is RELEASE_EVIDENCE_INTEGRITY_RISK, not merely a test-only exemption.
- POST_FIX_STATUS: FIXED for redirect delegation in the two covered files. Both gateway helpers (`_json`, `_form`) and the soak helper reject redirects before any delegated request. All relevant checks passed. Operator-selected initial destinations remain authorized.
- NEGATIVE_CONTROL: `run_negative_control.py` loads both original modules from BASE_HEAD into memory and runs the final behavioral tests without changing disk source. Exit 1: **42 failing redirect-confinement assertions, 21 passing tests**. Each of three helpers followed 14 prohibited redirect variants; three file-scheme cases were already refused. Fifteen direct-body confinement cases and three success controls passed. The same original implementation is the removed-fix mutation.
- POSITIVE_CONTROL: **70 targeted tests passed**, including all 63 new cases and seven existing gateway tests; **one surrounding HTTP qualification test passed**, exercising two real local station/job/export cycles. Loopback guard checks passed: three non-loopback connections and external DNS refused before network I/O, loopback listening permitted.
- LIMITATIONS: Mock HTTP/HTTPS/FTP handlers model redirect responses without resolving or contacting prohibited targets. `private.invalid` models a private-resolving hostname; actual DNS/rebinding is not tested. Numeric private, link-local, IPv6, mapped IPv4, integer/hex/short/percent-encoded/userinfo host variants are covered. Refusing all redirects avoids address-string filtering and DNS classification. Initial operator configuration, proxy environment, compromised Python/native code, and other network callers are outside this unit. The audit guard restricts cooperative Python socket operations and is not an OS network sandbox. This is not campaign-wide Qualification-v1 or a post-fix Snyk receipt.

## Scope and scanner mapping

BASE_HEAD: `d796f36b75e730a0bab71bdba564206174393719`

BASE_TREE: `39d23b7a8d395664329866d43a3fb9c97e8d83fb`

The isolated baseline contains nine `python/Ssrf` records: gateway line 64 and soak lines 28, 76, 79, 80, 83, 87, 88, 92. The eight soak locations all terminate at the same `request()` network sink and form one duplicate group. Thus two canonical SSRF sink groups are represented in the disposition ledger. The additional gateway form helper is covered proactively by the same fix/tests.

Only these product/tool files change:

- `demo/cloud_gateway/server.py`
- `scripts/qualification_active_http_soak.py`

Other R4-01 files are the behavioral test under `tests/security/`, evidence under `artifacts/security/r4-01/`, this report, and campaign disposition metadata. No archive code/test/evidence is included in this commit.

## Reproduction

Run from the repository root, with `PYTHONPATH` set to `artifacts/security/r4-01/loopback_guard` and the repository root (absolute paths for subprocess inheritance):

1. `python artifacts/security/r4-01/loopback_guard_check.py`
2. `python artifacts/security/r4-01/run_negative_control.py` (expected exit 1)
3. `python -m pytest tests/security/test_r4_01_network_authority.py tests/test_demo_cloud_gateway.py -q` (expected exit 0)
4. `python -m pytest tests/qualification/test_active_http_soak.py -q` (expected exit 0; requires loopback listening permission)

The guard is loaded by `sitecustomize` in the test process and Python server child. It installs an audit hook; it does not patch or rewrite the product code. Behavioral tests separately replace transports with in-memory handlers. Evidence source hashes bind the results to the tested file contents; a subsequent exact-commit receipt records the bounded commit SHA without claiming a self-referential commit hash.
