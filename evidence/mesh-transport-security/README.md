# SC-MESH transport and integrity hardening — review candidate

Base: integration/mesh-provider-continuity-20261025 at
`2a3e4ff9feb7bcdba01ea2f385f63103d103f223` (PR #546), fetched and
rechecked against the remote branch on 2026-10-28. No existing redirect,
proxy, or execution-admission HTTP redaction correction is reimplemented.

## Findings

- MeshWorkerClient already rejects remote plaintext HTTP, disables environment
  proxies with ProxyHandler({}), and refuses redirects using NoRedirect. Both
  GET and POST use that opener. HTTPS uses urllib's default certificate/hostname
  verification; this patch introduces no TLS bypass.
- The loopback exception intentionally supports local Station and SSH forwarding.
  Previously, the literal hostname `localhost` passed validation but was still
  resolved by the OS. A non-loopback resolver mapping would send plaintext bearer
  credentials and payloads to that address. This is a conditional exposure path,
  not evidence of deployment misconfiguration or exploitation. Numeric loopback
  needs no hostname mapping. The patch pins HTTP localhost to 127.0.0.1; IPv6-only
  listeners must explicitly use http://[::1]:PORT.
- urllib URL parsing can strip control characters and defer malformed port
  failures until request construction. Reject these inputs, missing hosts, port
  zero, backslashes, credentials (including empty userinfo), query and fragment
  delimiters before storing the base URL. Errors do not echo supplied URLs.
  HTTPS reverse-proxy path prefixes remain supported.
- A local process that occupies the configured port can receive the bearer token.
  Loopback does not authenticate a listener or prove SSH ownership. Trust the
  local host/users and the listener lifecycle. For SSH forwarding, verify the SSH
  host key, use ExitOnForwardFailure=yes, bind the local forward explicitly to
  127.0.0.1 (or ::1), and forward to the Station's loopback listener on the remote
  SSH host. A remote forwarding destination on another machine creates an
  unencrypted final leg if HTTP is used. On an untrusted/shared host, prefer
  end-to-end verified HTTPS. No live SSH/multi-host configuration was tested.
- Integrity failures were already observable: server.post(message) calls
  MeshState.admit_message, which catches parser ContractError, commits a durable
  mesh_dead_letters entry, then rethrows; do_POST returns HTTP 400. Routine access
  logs are deliberately suppressed. The prior test
  test_expired_message_not_replayed_and_integrity_failure_is_dead_lettered
  already covers persistence. Therefore "integrity events are unobservable" is
  incorrect for this integration candidate.

## Corrections

MeshIntegrityError remains a ContractError and provides stable code
MESH_PAYLOAD_DIGEST_MISMATCH only for a well-formed but mismatched digest.
Malformed digest syntax remains ordinary contract validation. The parser stays
free of logging side effects. At Station admission, a mismatch writes a distinct
message.integrity dead letter with that code and emits one WARNING record:
message=mesh_integrity_failure, event_code=MESH_PAYLOAD_DIGEST_MISMATCH,
operation=message.validation, outcome=rejected. No token, URL, payload, supplied
identifier, artifact reference, lease, or digest is included in this path's
telemetry. The existing HTTP 400 response remains unchanged and generic contract
failures retain their existing handling. Logging consumers can alert on the
stable event_code; no external alert delivery/configuration is claimed. Dead
letters retain the existing bounded retention policy; warning retention and
aggregation depend on the deployment's logging collector.

## Validation

Environment: Python 3.12.14, pytest 9.2.0, defusedxml 0.7.1, PyYAML 6.0.3 in an
isolated /tmp venv. The initial system Python invocation could not run tests
because pytest was absent. No test failure is concealed by that setup step.

`focused.log`: initial new transport/security cases plus existing SC-MESH-001
suite: **60 passed**. Subsequently added an authenticated real Station HTTP
integrity rejection test, included in the broader run below.

Reproduce broader affected run:

```sh
python -m pytest -q tests/station tests/continuity tests/modular tests/test_providers.py tests/qualification/test_provider_mission.py
```

Result: **287 passed, 69 subtests passed in 50.38s** (see affected.log).
Compileall for changed Python files and git diff --check also passed.

Fixtures use synthetic credentials, disposable SQLite state and local HTTP
servers. Redirect tests cover GET/POST with 301/302/303/307/308 and assert the
second listener receives zero requests. Proxy tests set all common proxy env
variables and remove bypasses. Tests cover allowed/rejected URL configurations,
inline/artifact digest mismatch, malformed digest classification, dead-letter
and log redaction, and authenticated HTTP 400 rejection without message admission.

No full release qualification, live SSH tunnel, native multi-host run, production
traffic, HTTPS deployment/certificate exercise, or independently verified review
is claimed. No authority checks or release gates are weakened. Independent review,
exact-head CI and complete release composition remain required.
**V1_RELEASE_HOLD remains active. Do not merge or deploy automatically.**
