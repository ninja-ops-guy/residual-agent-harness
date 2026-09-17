# Provider Gate Threat Model

The production SDK-load gate is designed to detect accidental browser-policy and deployment regressions, including service-worker header injection, path/scope mistakes, CSP/CORP/COEP incompatibility, broken provider helper publication, and external script load failure.

It is not a security proof of Puter, authentication, model behavior, or external service availability. It deliberately performs no credential or inference operation. RESIDUAL's candidate validation and verifier remain separate trust boundaries.
