# Boundary Change Qualification Rule

Any change that alters service-worker scope, browser response headers, provider helper location, external SDK URL/loading, Pages path layout, or navigation between Mission Control and provider setup is a boundary change.

Boundary changes require explicit review of both sides of the boundary and a test at the published-origin layer. Source inspection and local fixture tests are necessary but insufficient.
