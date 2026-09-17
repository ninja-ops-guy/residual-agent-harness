# Regression Policy Summary

The demo release process now treats browser policy, provider loading, provider behavior, deployment identity, and physical-device behavior as separate evidence domains. Changes must be qualified at the domain they can break.

The key prevention mechanism for the 2026-09-17 incident is a post-deploy public-origin test that loads the real Puter SDK while explicitly refusing authentication or inference. This complements, rather than replaces, deterministic provider fixtures.

Agents must read repository `AGENTS.md` and the release guardrail documents before changing these surfaces, and must stop merges when required evidence is missing or contradictory.
