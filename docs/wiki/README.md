# RESIDUAL Wiki

The RESIDUAL Wiki is the documentation and setup-assistant surface inside Command Station.

The existing `docs/` tree remains the canonical source. The wiki indexes it in place rather than copying documentation into a second content system.

## What users get

- full-text local search across readable Markdown/JSON/TOML/YAML/text documentation;
- browseable categories based on the existing `docs/` hierarchy;
- a grounded wiki agent that retrieves documentation before calling a model;
- explicit source paths and content hashes with every answer;
- setup-skill recommendations chosen by the host registry rather than invented by the model;
- bounded setup plans, generated snippets, and handoffs into existing Station controls.

Open Command Station and select **Wiki + setup agent** or press **6**.

## Trust boundary

Documentation is reference material, not execution authority.

A page can contain examples, shell commands, prompts, or even hostile instructions. The wiki assistant treats the retrieved text as untrusted context. It cannot create a new setup skill, widen a skill's inputs, or execute a command copied from a document.

Setup skills are declarative JSON manifests shipped under:

`residual/wiki/skill_manifests/`

The host parses and validates those manifests. Skills can return:

- documentation to read;
- ordered setup/verification steps;
- safe command previews with secret placeholders;
- generated configuration snippets;
- navigation handoffs into an existing Station surface.

They do **not** execute arbitrary shell commands or silently modify external services.

## Built-in skills

| Skill | Purpose |
| --- | --- |
| `local-model` | Set up/test a local Ollama-compatible model in Model Workshop |
| `openai-compatible` | Connect an approved cloud/OpenAI-compatible provider without giving the wiki credentials |
| `distributed-worker` | Connect another trusted runner while verification stays on the coordinator |
| `module-development` | Create/validate a RESIDUAL module entry point |
| `cicd-integration` | Map RESIDUAL qualification/evidence into CI/CD |
| `enterprise-pilot` | Walk through enterprise pilot/governance/security documentation |

## API

Authenticated Command Station endpoints:

- `GET /api/wiki` — index statistics and skill catalog
- `GET /api/wiki/search?q=...` — deterministic documentation search
- `GET /api/wiki/doc?path=...` — exact indexed document
- `GET /api/wiki/skills` — skill metadata
- `POST /api/wiki/ask` — retrieve docs, then ask the selected local/cloud model
- `POST /api/wiki/skills/plan` — validate inputs and build a skill plan
- `POST /api/wiki/skills/run` — same bounded skill execution surface; returns artifacts/handoffs and reports `side_effects: none`

The wiki defaults to the local model route. Selecting cloud is explicit.

## Documentation location

When running from the repository or the bundled Command Station image, the wiki finds the repository `docs/` directory automatically.

For a custom deployment, set:

`RESIDUAL_DOCS_ROOT=/absolute/path/to/docs`

The index refuses symlinks and path traversal outside that root.

## Adding a skill

Add a JSON manifest to `residual/wiki/skill_manifests/` with:

- a stable identifier;
- title/category/summary;
- search keywords;
- supporting documentation paths;
- typed, bounded inputs;
- ordered setup steps.

Do not add secrets as skill inputs. A skill that needs credentials should hand the user to the existing credential-owning UI or secret manager.

New side-effecting integration actions require a separately reviewed host handler. A documentation manifest alone cannot grant side-effect authority.

## Why the wiki does not become a second documentation tree

The documentation you have already been maintaining remains versioned with source, tests, specs, enterprise runbooks, research notes, and evidence. The wiki is an indexed interface over that tree.

That means a documentation PR updates both human-readable source and agent-visible knowledge in one place. The wiki's index hash changes automatically when indexed document content changes.
