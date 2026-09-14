# Residual browser demo / GitHub Pages

A responsive teaching demo for the evidence-first control loop. This is separate
from Command Station and Python Factory. It does not execute models, tools, OS
sandboxes, M2 workers, the M3 bus, or canonical M4 integration.

## One publishing authority

`.github/workflows/pages.yml` is the sole Pages publisher. It replaces the older
workflow that published `site/`. The legacy `site/` source is retained for review,
but no longer has an independent deployment job. There is no parallel
`pages-demo.yml`: two publishers to the same Pages site can overwrite each other,
even when their individual CI runs are green.

`tests/test_pages_publisher.py` enforces a single official deploy-pages action,
read-only build permissions, main-only deployment with successful-build dependency,
public artifact directory, environment, disabled checkout credentials, pinned
Actions and trigger coverage. Adversarial tests reject duplicate publishers and
weakened guards. This is a review-controlled workflow contract, not a claim to
detect arbitrary malicious deployment hidden in scripts or remote workflows.

The demo workflow validates PRs but never deploys them. Changed workflow files,
demo files, or the publisher regression test trigger checks; a relevant main
push or a manual dispatch on main may deploy only after those checks succeed.
The deployment job alone receives Pages/OIDC permissions, honors github-pages
environment approvals, and uses a shared Pages concurrency group.

## Activation and verification

The default target is:

```text
https://ninja-ops-guy.github.io/residual-agent-harness/
```

That is a target, not evidence that this version is live. In repository Settings
-> Pages -> Build and deployment -> Source, select GitHub Actions if it is not
already selected. Review and manually merge this PR after applicable checks pass.
Then require a successful `Publish reviewed main to Pages` job and inspect the
returned URL before claiming deployment. A skipped PR deployment is expected.

When enabling Pages after merging, manually run Actions -> GitHub Pages demo on
main. Honor any required environment reviewers; do not bypass protection rules.
No workflow here merges PRs, alters branch protections or changes Pages settings.

Official documentation:
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## Interactive scenarios and claim boundary

| Scenario | Checks | Final handoff |
| --- | --- | --- |
| Verified acceptance | PASS / PASS / PASS | ACCEPTED, sorted artifacts |
| Faulty candidate | FAIL / PASS / PASS | BLOCKED, no complete output |
| Missing evidence | PASS / UNKNOWN / PASS | BLOCKED, uncertainty retained |
| Integration conflict | PASS / PASS / PASS | CONFLICT, differing bytes at a shared path |

Small JavaScript checks evaluate scripted values; the composer detects differing
bytes rather than assigning conflicts from worker count. These are demo-only
rules, not a second Factory implementation. Downloaded JSON uses the separate
`residual.pages-simulation.v1` schema with `simulation: true`, `signed: false`,
source revision and limitations. Observations are illustrative, not measurements.
No model-quality, containment, token/cost-saving or speedup claim follows from it.

## Local preview

Use a fresh output directory; the builder refuses to overwrite existing output.

```bash
python demo/build.py --output /tmp/residual-demo-preview --revision "$(git rev-parse HEAD)"
python -m http.server 8080 --bind 127.0.0.1 --directory /tmp/residual-demo-preview
```

Open the local HTTP server; file URLs do not support the required module-loading
behavior. Without a revision argument a build is labeled local-unversioned.

## Tests

```bash
python -m pip install 'PyYAML>=6'
python -m unittest discover -s tests -p test_pages_publisher.py -v
node --test demo/tests/model.test.mjs
python -m unittest discover -s demo/tests -p 'test_*.py' -v
python demo/build.py --output /tmp/residual-demo-qa
python -m pip install -r demo/tests/requirements.txt
python -m playwright install --with-deps chromium
python demo/tests/browser.py --site /tmp/residual-demo-qa --screenshots /tmp/residual-demo-screenshots
```

Browser checks cover desktop 1440px and touch-emulated 390px/360px at both root
and project paths, all scenarios, actual JSON downloads, reset/cancellation,
overflow, assets, no backend requests, and CSP connection denial. Chromium touch
emulation is not physical iPhone/Safari validation. CI retains screenshots and
the built public artifact. Node/Python/QA dependencies are not visitor dependencies.

## Security and ownership

Only six allowlisted files from `demo/site/` are published. Builder tests reject
symlink assets, unsafe revisions and existing output directories. No repository
source, tests, runtime evidence or credentials are copied to the public output.
Relative assets need no CDN, remote fonts or analytics. The restrictive meta CSP
includes connect-src 'none', object-src 'none', base-uri 'none', form-action 'none'.
There is no API-key entry, upload, eval, browser storage or live backend. Dynamic
text uses textContent. Meta CSP does not implement HTTP-only frame-ancestors;
this credential-free demo is not a security boundary for real worker execution.

Top-level Actions are pinned to full SHAs. Upstream composite action transitive
references and QA dependency resolution remain their own supply-chain boundary.
The only existing deployment workflow modified is pages.yml; runtime, canonical
verifiers, package metadata, generated status and root README are untouched.
The demo can be reviewed independently of the M2/M3/M4 research/benchmark stack.
