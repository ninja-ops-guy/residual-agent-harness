# RESIDUAL / Command Station

**Markdown missions. Local runners. Cloud backup. Evidence at every handoff.**

A retro operations console for a hybrid agent harness, integrating [LDD Kit](https://github.com/ninja-ops-guy/LDD-Kit) with RESIDUAL's verification approach and your modular provider/observation packages.

## Launch

Windows: **Start-Station.cmd**. macOS: **Start-Station.command**. Linux: `bash Start-Station.sh`.

With Docker running, the launcher builds one image containing the app, Python, Git, Node.js/npm, and Ollama. Open **http://localhost:8765**, run the training mission, then download and select a local model in Model Workshop. Model weights download on demand; this source bundle is not an offline model distribution.

Native mode requires Python 3.11+ and Git, with no pip dependencies:

```bash
python3 -m residual.station.server --open
# Or: python3 -m residual serve --open
```

[START-HERE.md](START-HERE.md) covers installation, GPU options, repositories, storage, and troubleshooting.

## Included

- Markdown import, model-drafted specs, a mission board, local triage and bounded dependency waves.
- Immutable goal contracts, ordered verification (including UNKNOWN), action quarantine, loop brakes and downloadable run-control receipts.
- A frozen extension registry, revision-bound task receipts, prerequisite propagation and revalidated receipt-aware caches.
- SecOps inspection before Git staging, structural trajectory recording, a read-only TUI collector and receipt-indexed local memory.
- Opt-in NetOps, HITL and mesh lifecycle adapters; device execution, operator authentication and network transport remain host responsibilities.
- Parallel local/cloud implementation in isolated Git worktrees; automatic residual escalation after two failed local attempts when cloud processing is allowed.
- Deterministic acceptance checks, revision-bound model review, stale approval rejection, rebase/rechecks, and accumulated integration checks.
- LDD event validation, transactional SQLite state, leases, restart recovery, shared comms and deterministic report generation.
- An automatic, three-role cloud assessment after permitted live batches: planning, diagnosis and integration analysis. Reports are advisory and cannot approve code.
- In-interface Ollama installation, start/stop, model downloads with progress, selection, unloading, BYO provider routes, connection tests and a playground.
- Seven provider routes: OpenAI, compatible endpoints, Anthropic, Gemini, Azure, Bedrock and Ollama; provider-scoped keys and budgeted failover.
- An observation console with durable traces, correlation IDs, chain verification, JSONL export and optional recording.
- An authenticated distributed inference client. The coordinator owns code execution, review and acceptance.
- Evidence, patches, project Markdown and verified source release ZIP downloads.

The training mission uses scripted proposals with real Git/check execution. It demonstrates the workflow, not model quality or token savings. Task authors declare scope and tests; the station does not implement unrestricted repository browsing or autonomous shell access. Native project command checks are opt-in and are not an OS sandbox. Export creates a source release, not a production deployment.

Version **0.4.0** integrates the uploaded Tracks 2–8 with the [Track 1 foundation](docs/roadmap/TRACK-1-IMPLEMENTATION.md). Mesh is a single-chain protocol prototype, and HITL requires a host authenticator. No real-model quality or token-savings claim is made.

## Documentation

- [Controlled studies, independent grading, and contract stress tests](docs/controlled-evaluation.md)

- [World-class roadmap, first track and delegation boundaries](docs/roadmap/README.md)

- [Goal contracts, quarantine and mission loop controls](docs/station/RUN-CONTROL.md)
- [Modular providers, observations, and capability limits](docs/station/MODULAR-LAYERS.md)
- [Architecture and invariants](docs/station/ARCHITECTURE.md)
- [Specification format](docs/station/SPECIFICATION.md)
- [Distributed workers](docs/station/DISTRIBUTED.md)
- [Validation evidence](docs/station/VALIDATION.md)
- [LDD provenance](vendor/ldd-kit/PROVENANCE.md)
- [Research and measurement](docs/station/RESEARCH.md)
- [Original harness and research CLI](HARNESS.md)

The station and configured CLI routes use the modular adapters through RESIDUAL's bounded provider bridge, strict JSON, hashing and usage types. Software-task coordination is a separate module; arbitrary code tasks do not use the original obligation verifier or evidence-window algorithm. The original CLI and benchmarks remain available.

## Verify and package

```bash
python3 -m unittest discover -s tests -v
node --check residual/station/static/app.js
# Optional browser QA:
npm install
npx playwright install chromium
npm run test:ui
# Bundle source and Git history:
python3 scripts/bundle_station.py
```

The web interface is static HTML/CSS/JS served by Python. No frontend build, CDN, analytics, or cloud account is required.

## Publish your repository

The bundle contains the committed Git history and a publishing script. With GitHub CLI installed and authenticated, run:

```bash
gh auth login
python3 scripts/publish.py --owner YOUR_GITHUB_USERNAME --name residual-agent-harness
```

The script creates a private repository and pushes `main`. Use `--dry-run` to inspect the commands. It refuses to overwrite an existing remote or publish uncommitted source changes.
