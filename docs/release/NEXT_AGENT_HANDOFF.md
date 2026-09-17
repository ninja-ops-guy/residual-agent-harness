# Next Agent Handoff

Current hardening objective: prevent public demo/provider regressions from passing adjacent green tests.

When continuing this work, do not remove or weaken the published real-SDK load gate. Extend hardening only when new evidence identifies another untested boundary. Prefer small executable acceptance tests over prose-only promises, and update the acceptance matrix/agent instructions whenever a new release claim is introduced.

Before merging, rebase/refresh onto the intended current main or provider-fix lineage, run fresh exact-head qualification, and preserve first-failure evidence. After merge, the first production Pages deployment is mandatory evidence.
