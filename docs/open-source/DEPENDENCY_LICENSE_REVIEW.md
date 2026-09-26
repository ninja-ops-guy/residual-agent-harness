# Direct dependency license review

Snapshot based on the current project manifests. This is a direct-dependency review, not a complete transitive SBOM.

| Dependency | Role | Declared license |
|---|---|---|
| defusedxml >=0.7.1,<1 | runtime | Python Software Foundation License |
| cryptography >=43 | optional marketplace/factory | Apache-2.0 OR BSD-3-Clause |
| PyYAML >=6 | optional factory/test | MIT |
| pytest >=8 | test | MIT |
| playwright ^1.58.0 | dev/browser QA | Apache-2.0 |

The vendored `vendor/ldd-kit/` subtree contains its own LICENSE and remains governed by that license.

## Release gate

Before a public binary/container/package release:

1. generate a machine-readable dependency inventory/SBOM;
2. inspect transitive dependencies;
3. retain required notices/license texts;
4. verify container/base-image licensing separately;
5. block release on unknown or incompatible licensing.

No third-party dependency becomes Apache-2.0 merely because RESIDUAL Open Core uses it.
