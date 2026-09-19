# Copilot Studio enterprise operations

## Monitoring

Alert on repeated 401/403/409/429 responses, mission lease expiry, ciphertext verification failure, sandbox infrastructure errors, repeated worker failures, excessive queue depth, stale missions, and HITL denial/replay. Export only redacted identifiers/hashes; never bearer tokens, prompts, source content, credentials, or plaintext evidence.

## Key rotation

Entra signing keys rotate through JWKS automatically. Queue encryption/signing keys are provided through the RESIDUAL CryptoProvider abstraction and should be backed by enterprise KMS/HSM. Rotate service credentials and encryption keys under change control; preserve the ability to decrypt retained evidence according to the organization's retention schedule.

## Backup/restore

Back up the encrypted queue/evidence database through the platform's durable backup mechanism. Backup storage inherits the same data classification as engineering evidence. Restoration must preserve file ownership/permissions and must be tested in a non-production environment. A restored queue with uncertain active worker leases must fail closed; do not automatically replay uncertain work.

## Retention/legal hold

Apply organization retention and legal-hold policy to mission metadata/evidence. Do not implement ad-hoc deletion that bypasses RESIDUAL's existing compliance/legal-hold controls. Evidence needed for an active investigation, release record, or legal hold must remain immutable for the required window.

## Incident response

If connector credentials, KMS keys, or service identity are suspected compromised: disable connector access or API ingress, revoke/rotate affected credentials, revoke active sessions/worker leases where possible, preserve the encrypted evidence ledger, investigate redacted audit events, and requalify the exact deployment configuration before re-enabling.

## Recovery objectives

The HTTP tier is stateless except rate-limit state. Authorization ownership and mission queue state are durable. Workers use leases. Failed or expired leases are not automatically replayed because execution outcome may be uncertain. Operator recovery must inspect evidence and deliberately reissue work under a new mission/attempt when appropriate.
