# Hardening Change Scope

This hardening is release/test/documentation work around the provider helper boundary. It does not modify M4/Factory implementation, verifier authority, evidence schemas, provider worker-envelope acceptance, call budgets, or model substitution rules.

The only runtime boundary inherited from the underlying provider fix is the narrow same-origin `/provider/` bypass in the root COI service worker. `/demo/` remains isolated.
