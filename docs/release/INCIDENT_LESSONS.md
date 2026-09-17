# Durable Incident Lessons

- Browser security policy is part of the runtime, not merely deployment plumbing.
- Service-worker scope can couple pages that appear architecturally separate.
- A fixture that replaces a third-party resource removes the exact network/policy behavior needed to test whether that resource can load.
- Generated/local acceptance and published-origin acceptance answer different questions.
- Responsive viewport simulation and physical browser-engine qualification answer different questions.
- A green aggregate job can hide NOT_RUN layers unless evidence is explicitly typed.
- The safest regression fix is the narrowest boundary repair plus a test at the layer that originally escaped.
