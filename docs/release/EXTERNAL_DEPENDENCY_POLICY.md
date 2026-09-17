# External Dependency Qualification Policy

When the public demo intentionally depends on an external browser resource, production qualification must include a bounded real-resource check at the layer where browser policy applies.

The check must minimize side effects. For Puter this means SDK initialization only: no sign-in, account creation, model enumeration, or inference in CI.

A real-resource failure may be caused by RESIDUAL policy, the external service, DNS/networking, or browser behavior. Preserve the failure and classify it accurately. Do not silently replace the real check with a fixture; deterministic fixtures remain a separate gate.
