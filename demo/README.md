# Residual browser demo / GitHub Pages

A dependency-free, responsive teaching demo for the evidence-first control loop.
It is separate from Command Station and the Python Factory runtime. It does not
execute models, tools, OS sandboxes, M2 workers, the M3 evidence bus, or M4 integration.

## Publish

The proposed default project URL is:

```text
https://ninja-ops-guy.github.io/residual-agent-harness/
```

This URL is a deployment target, **not a claim that publication has completed**.

1. Review and manually merge the demo PR into `main` after its checks pass. No
   workflow in this change merges a PR or changes another branch.
2. In repository **Settings → Pages → Build and deployment → Source**, select
   **GitHub Actions**. This one-time setting requires repository access that can
   administer Pages; the regular workflow token cannot reliably enable a new site.
   The setting can be selected before merging to make the first push deploy directly.
3. Open **Actions → GitHub Pages demo**. After the PR is merged, run the workflow
   on `main` if the first deployment failed because Pages was not enabled yet.
   The `Publish reviewed main to Pages` job must succeed before calling the site live.

With no custom domain, the successful deployment URL should match the project URL
above. If the `github-pages` environment has required reviewers, approve that
specific deployment there. Do not disable protection rules to bypass approval.

The workflow builds and tests PRs but **never deploys from a PR**. Pushes to `main`
that change the demo trigger a deployment; manual dispatch only deploys when the
selected ref is `main`. Deployment has a hard dependency on successful demo tests.
No provider credentials, personal tokens, backend endpoints, or custom domain are
required for the site. This patch does not alter Pages settings through the API.

Official setup references:
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## What visitors can try

| Scenario | Check outcomes | Final handoff |
| --- | --- | --- |
| Verified acceptance | PASS / PASS / PASS | ACCEPTED; stable, sorted artifacts |
| Faulty candidate | FAIL / PASS / PASS | BLOCKED; no complete output |
| Missing evidence | PASS / UNKNOWN / PASS | BLOCKED; uncertainty stays visible |
| Integration conflict | PASS / PASS / PASS | CONFLICT; different bytes share a path |

The JavaScript verifiers actually check the scripted candidate values, and the
small composer detects conflicting bytes rather than assigning a metric based on
worker count. These are **demo-only rules**, not a second implementation of the
Factory specification. Full candidate records and observations can be downloaded.
Each export uses a separate `residual.pages-simulation.v1` schema and explicitly
carries `simulation: true`, `signed: false`, its source revision, and limitations.
The sequence is illustrative, not a measured execution trace. There are no claims
of real model quality, reliability improvement, tokens saved, cost, or speedup.

## Local preview

From the repository root, with Python 3.11+:

```bash
python demo/build.py --output /tmp/residual-demo-preview
python -m http.server 8080 --bind 127.0.0.1 --directory /tmp/residual-demo-preview
# Open http://127.0.0.1:8080/
```

Choose a new output directory on each build. The builder refuses existing
outputs rather than deleting files. Pass `--revision "$(git rev-parse HEAD)"`
to bind a preview to a commit; otherwise it is labeled `local-unversioned`.
Serve over HTTP; directly opening `index.html` as a `file://` URL is not supported
because the application uses JavaScript modules.

## Verification

Node 22 and Python 3.11+ are used for tests; neither is required by a visitor.

```bash
node --test demo/tests/model.test.mjs
python -m unittest discover -s demo/tests -p 'test_*.py' -v
python demo/build.py --output /tmp/residual-demo-qa
python -m pip install -r demo/tests/requirements.txt
python -m playwright install --with-deps chromium
python demo/tests/browser.py --site /tmp/residual-demo-qa --screenshots /tmp/residual-demo-screenshots
```

An existing Chromium executable can be selected with `DEMO_CHROMIUM=/path/to/chromium`.
The browser suite exercises 1440px desktop and 390px/360px touch layouts at both
`/` and `/residual-agent-harness/`. It checks all scenarios, actual JSON downloads,
UNKNOWN/conflict states, timer cancellation, no horizontal overflow, asset loading,
absence of backend/provider requests, and CSP denial of a connection probe.
Touch emulation is not physical iPhone/Safari validation. CI retains screenshots
in `demo-browser-screenshots` and the public bundle in `github-pages` artifacts.

## Security and ownership boundaries

- `demo/build.py` publishes only six allowlisted files from `demo/site/`. It does
  not copy the repository, documentation, tests, credentials, or runtime evidence.
  Symlink assets and unsafe revision strings are rejected.
- All assets use relative URLs so project-path hosting works without a bundler,
  router fallback, CDN, remote fonts, analytics, or third-party runtime scripts.
- The page uses a restrictive meta CSP, including `connect-src 'none'`,
  `object-src 'none'`, `base-uri 'none'`, and `form-action 'none'`. No API-key entry,
  file upload, eval, local storage, service worker, or live backend connection is
  provided. Dynamic DOM content uses `textContent`, not HTML interpolation.
- Meta CSP cannot supply HTTP-only protections such as `frame-ancestors`.
  This is a credential-free static demo, not a security boundary for real execution.
- The workflow grants read-only contents access to the test job, disables persisted
  checkout credentials, and grants Pages/OIDC write permissions only to deployment.
  Top-level actions are pinned to full commit SHAs; transitive dependencies still
  follow those upstream action implementations and pinned QA package metadata.
- No `residual/factory/*`, M2/M3/M4 files, canonical verifier, existing workflows,
  package metadata, or generated implementation-status files are changed. There
  are no dependencies on the active M4/EVAL/FB001/FB002/FB003 PR stack.
- The root README is intentionally untouched to avoid overlap with concurrent
  documentation PRs. Add the demo URL there once a deployment has succeeded.
