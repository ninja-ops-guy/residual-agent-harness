# RESIDUAL v1 Sensitive Evidence Handling

**Status:** PREPARATION POLICY — applies to release evidence handling, not product runtime authority.

Release evidence should prove credential behavior without making credential values part of the reviewer-facing bundle.

## Rule

Credential values, private keys, bearer/session tokens, API keys, cookies, launch capabilities, and private tunnel URLs MUST NOT be copied into ordinary release evidence.

When an original artifact necessarily captured sensitive material:

1. preserve the original only in a restricted/quarantined evidence location;
2. record its SHA-256 and provenance without publishing its secret content;
3. produce a redacted derivative for normal review;
4. record the derivative SHA-256 and the original-source SHA-256;
5. state exactly which fields were redacted;
6. verify that the redacted artifact still proves the intended invariant;
7. rotate/revoke the exposed credential when operationally safe if it may still be live;
8. never rewrite history to pretend the original capture did not occur.

A frozen sensitive artifact may remain historical evidence, but its immutability is not a reason to distribute the credential.

## Preferred evidence pattern

```text
restricted original
  source_sha256 = <hash>
        |
        v
reviewed redaction
  redacted_fields = [<names only>]
  source_sha256 = <original hash>
  stored_sha256 = <redacted hash>
        |
        v
reviewer-facing manifest
```

The reviewer-facing manifest should retain field names, booleans such as credential-present, denial/error class, candidate identity, timestamps, and cryptographic fingerprints where those are public identity material.

## Fail-closed conditions

Stop evidence publication if:

- a credential value appears in a normal bundle;
- a redaction cannot be shown to preserve the required proof;
- a secret-bearing artifact is uploaded to a public/shared location;
- provenance between original and redacted derivative is lost;
- a supposedly redacted value can be reconstructed from retained fields.

## Release packet

The final v1 release packet should contain only redacted/reviewer-safe evidence and hashes/provenance for restricted originals. It must not require reviewers to possess live credentials to verify release claims.
