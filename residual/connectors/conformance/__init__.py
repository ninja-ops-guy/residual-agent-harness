"""Track M — connector contract conformance suite and certification matrix.

Requirement IDs (RFC 2119):

- M-R1: Every connector submitted for certification MUST be driven through
  the contract scenarios in this suite using an injected scripted transport;
  no live network is permitted in the suite.
- M-R2: The suite MUST cover, at minimum: auth expiry/re-auth, pagination,
  retry with backoff, HTTP 429 handling, duplicate webhook delivery,
  malformed responses, and idempotency-key stability across retries.
- M-R3: Each scenario MUST produce a pass/fail result with evidence
  (recorded requests, waits, errors) and MUST NOT abort the remaining
  scenarios on failure.
- M-R4: The suite MUST emit a certification matrix as JSON and as Markdown.
"""
from .harness import (
    CertificationMatrix,
    CheckResult,
    ConformanceSuite,
    ResilientConnector,
    ScriptedTransport,
    run_conformance_suite,
)

__all__ = [
    "CertificationMatrix", "CheckResult", "ConformanceSuite", "ResilientConnector",
    "ScriptedTransport", "run_conformance_suite",
]
