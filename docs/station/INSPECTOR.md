# Residual Inspector (px0)

Residual Inspector integrates [px0](https://github.com/px0-ai/px0) as an optional read-only human inspection sidecar. px0 is an observation surface only: it does not approve work, mutate accepted state, run workers, or bypass RESIDUAL verification and integration gates.

## Trust model

An inspection session is bound to an exact clean Git snapshot before px0 starts:

- `HEAD` commit;
- `HEAD^{tree}` tree hash;
- resolved workspace path;
- px0 version;
- SHA-256 of the local px0 binary;
- the upstream px0 commit against which the integration was qualified.

When px0 exits, RESIDUAL recomputes the snapshot. If HEAD/tree changed or the worktree became dirty, the session exits with status `3` and reports that the review became stale. A stale review must not be treated as approval evidence.

px0 remains read-only and Git-aware. Residual does not give it acceptance or integration authority.

## Qualified px0 build

The integration currently pins:

- px0 version: `0.1.2`
- upstream commit: `57539720bad363980ef6dd80febbc925ffab214f`

Residual refuses to launch a different px0 version. The launch receipt records the actual binary SHA-256 so a review can be tied to the concrete local executable, not just its version string.

## Usage

Install or build the pinned px0 release separately, then run:

```bash
residual inspector /path/to/clean/git/worktree
```

Useful options:

```bash
residual inspector . --no-open
residual inspector . --port 7777
residual inspector . --receipt runs/inspection.json
residual inspector . --px0 /absolute/path/to/px0
```

The default policy intentionally uses:

- loopback only (`127.0.0.1`);
- telemetry disabled (`-no-telemetry`, `DO_NOT_TRACK=1`, `PX0_TELEMETRY=0`);
- language servers disabled (`-no-lsp`) so inspection does not spawn or install semantic tooling implicitly;
- Git awareness enabled for read-only diff inspection.

Use `--lsp` only when the operator explicitly wants local language-server processes. Residual does not invoke px0's `--update` path.

## Receipt

`--receipt` writes a JSON launch receipt with the bound Git snapshot and inspection-tool identity. Example fields:

```json
{
  "schema_version": 1,
  "tool": "px0",
  "tool_version": "0.1.2",
  "upstream_commit": "57539720bad363980ef6dd80febbc925ffab214f",
  "binary_sha256": "...",
  "workspace": "/absolute/path/to/worktree",
  "head_commit": "...",
  "tree_hash": "...",
  "url": "http://127.0.0.1:7777",
  "lsp_enabled": false,
  "telemetry_enabled": false,
  "launched_at": "..."
}
```

This receipt establishes what the operator inspected; it is not itself an approval or correctness certificate.

## Intended Station/Factory use

For a candidate worktree, launch the inspector against the already committed candidate revision. Human review can then use px0's code navigation, Git diff, search, symbols, references, and call trails while RESIDUAL remains the sole owner of review state and deterministic integration.
