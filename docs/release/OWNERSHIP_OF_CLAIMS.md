# Ownership of Demo Release Claims

Automated checks may establish only the claims they directly exercise. Human/agent summaries must preserve that scope.

- `browser_smoke.py` may establish guest/browser/workbench behavior and deterministic provider-fixture behavior.
- `provider_sdk_smoke.py` may establish published real Puter SDK initialization only.
- Neither script establishes real provider authentication or inference unless explicitly extended and separately governed.
- Physical-device claims belong only to retained evidence from that actual device/runtime class.

Agents reviewing CI must inspect what the test actually did, not infer capability from a green job name.
