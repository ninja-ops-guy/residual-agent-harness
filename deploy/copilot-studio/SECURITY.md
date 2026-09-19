# Copilot Studio deployment security gates

The managed Power Platform solution is a packaging boundary, not the RESIDUAL authorization boundary.

Required before production activation:

- Entra Conditional Access/MFA/compliant-device policy is assigned to the intended engineering population.
- The RESIDUAL API uses tenant-specific Entra issuer/JWKS, `access_as_user`, API audience, and connector-client allowlist.
- Department group values are Entra object IDs, not display names.
- Power Platform DLP prevents unapproved connectors from being combined with the engineering agents.
- The custom connector is configured with end-user delegated authentication/OBO; maker credentials are not used for user-specific missions.
- Production queue encryption uses a KMS/HSM-backed `CryptoProvider`, not `LocalDevCryptoProvider`.
- Public API ingress has TLS, reverse-proxy/WAF controls, distributed throttling, request timeouts, and central audit forwarding.
- External-write actions require an exact-head RESIDUAL HITL challenge and cannot be authorized solely by Copilot confirmation UI.
- Managed solution ZIP SHA-256 and deployment configuration hash are included in the enterprise-readiness bundle.
- Agent Library template remains Inactive until the test-environment import and hybrid-Entra walkthrough pass.
