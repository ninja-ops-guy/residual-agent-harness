# Reference architecture: compliance audit

Use read-only evidence collectors at the async periphery and bind normalized evidence into receipts. Verifiers check policy requirements deterministically where possible. Successful receipt graphs are indexed into epistemic memory; failed runs are not. Structured logs contain only timestamp, run/goal IDs, event kind, and a payload hash so model outputs, secrets, and PII do not leak into the audit stream.
