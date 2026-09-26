# RESIDUAL Command Station

Your local agent workshop: Markdown missions, parallel runners, LDD events, review gates, and Ollama in one retro interface.

## Fastest start: complete Docker runtime

1. Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/), or Docker Engine with Compose on Linux.
2. Extract the complete bundle into a writable directory.
3. Windows: double-click **Start-Station.cmd**. macOS: run **Start-Station.command** (or `bash Start-Station.sh` in Terminal). Linux: `bash Start-Station.sh`.
4. Open **http://localhost:8765**. First build downloads the runtime; subsequent launches reuse it.
5. Click **Run training mission**. It makes real commits, executes acceptance checks, and produces a release ZIP using scripted proposals, without an LLM.
6. Open **Model workshop**. Download a model, select **Use as runner**, and test the connection.

The single container includes Python, Git, Node.js/npm and Ollama with its runtime libraries. SQLite and the web server are built into Python. There is no frontend build or cloud account requirement. Model weights download on demand from the same interface. Weights, Docker images, GPU drivers, and all host operating-system prerequisites are **not embedded in the source ZIP**; the first setup needs internet access.

The supported v1 Compose profile is **local-workstation only**: Docker publishes Station on host loopback (`127.0.0.1:8765`) while Station binds the container interface so the port mapping can reach it. The Compose file declares an explicit local-container exposure policy, and Station refuses that policy outside a recognized container runtime or when Host/Origin values are not loopback-only. This is not an internet-facing deployment mode. Docker-daemon administrators and containers deliberately joined to the same Docker network are inside the local container trust boundary; use the separate authenticated-TLS remote exposure mode for any non-local deployment. Running the image directly without the Compose policy remains fail-closed.

For NVIDIA acceleration on a configured NVIDIA Container Toolkit host:

```bash
docker compose -f compose.yaml -f compose.nvidia.yaml up --build -d
```

For Apple Silicon GPU acceleration, use native mode and the native Ollama runtime; a Linux container does not give Ollama access to Metal.

## Native mode

Requires Python 3.11+ and Git. No pip packages are needed to run the station.

```bash
python3 -m residual.station.server --open
```

Windows equivalent: `py -3 -m residual.station.server --open`.

Model Workshop can download an official, SHA-256-verified Ollama runtime into the station's data directory on Windows x64, macOS x64/ARM64, and Linux x64/ARM64. Native Linux extraction also requires `zstd`; the Docker package includes it. Alternatively, connect an existing Ollama installation. Model downloads and loading/unloading remain in the UI.

Python 3.11 should be a current patch release (tar extraction uses the standard `data` filter). If the host blocks runtime downloads, install Ollama from [the official download page](https://ollama.com/download), start it, then refresh the workshop.

## Your first real project

1. Commit or stash changes in your source Git repository.
2. In Docker mode, put or clone the repository under the bundle's `projects/` directory. Its UI path is `/projects/your-repo`. That input mount is read-only; candidates are created in the station's writable data volume. Native mode accepts a local repository path.
3. Click **New mission**, then **Load template** or import a Markdown file. Replace the training tasks with your project's requirements. A model can draft the manifest, but you inspect it before import.
4. Declare exact files, context, dependencies and acceptance checks. Enable project command checks only for a project whose commands and generated code you trust. The default built-in checks do not launch code.
5. Optionally enable cloud processing for this project and configure an OpenAI-compatible endpoint in Model Workshop.
6. **Triage locally**, inspect the baseline, then **Run mission**. The coordinator runs dependency waves, bounded repair attempts, review, and integration checks.
7. Open task cards to inspect checks, patches, review receipts, and failure findings. Escalate unresolved tasks to cloud if desired.
8. **Export verified release** after all tasks are integrated. This creates a source ZIP, not a production deployment.

## Storage and stopping

- Native: `~/.residual/station`, or `--data PATH`. API keys stay in the local settings database; protect this directory and your OS account.
- Docker: the `residual-station_station-data` named volume persists projects, keys, events, Ollama models, and candidates. `docker compose stop` preserves it. Do not delete that volume if you want to keep your work.
- The browser interface is served at localhost. The default configuration does not expose it to the internet.
- Downloading a model can take several minutes and several GB. Repeating a failed model pull lets Ollama reuse previously downloaded layers.
- Setup/playground calls are separate from per-project accounting. Project call counts, reported tokens, unknown usage, and request bytes are visible in Diagnostics.

For architecture, command-execution limits, distributed runners, and testing evidence, see `docs/station/`.


## Upgrade to 0.3: your modular layers

Stop the old station, extract this bundle, and run the platform launcher. Reuse the same data directory (native default or Docker volume) to retain missions and settings. The new observation tables are added on startup; existing LDD task history stays authoritative. Keep a backup of the data directory when upgrading an active installation.

Open Model Workshop to select OpenAI, an OpenAI-compatible endpoint, Anthropic, Gemini, Azure, Bedrock, or Ollama. Save the provider's credentials and optional fallback order, then run a connection test. Open Diagnostics → Observation console to inspect a trace or download JSONL. No new pip dependency is required. See [the modular integration guide](docs/station/MODULAR-LAYERS.md) for setup, environment variables, provider capabilities and migration details.
