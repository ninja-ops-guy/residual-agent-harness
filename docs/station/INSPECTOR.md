# Residual Inspector (px0)

Residual Inspector integrates [px0](https://github.com/px0-ai/px0) as an optional human inspection sidecar. px0 is an observation surface only: it does not approve work, mutate accepted state, run workers, or bypass RESIDUAL verification and integration gates.

## Trust model

An inspection session is bound to an exact clean Git snapshot before px0 starts:

- `HEAD` commit;
- `HEAD^{tree}` tree hash;
- resolved workspace path;
- px0 version;
- SHA-256 of the local px0 binary;
- the exact upstream commit tagged as px0 `v0.1.2`.

Residual authenticates the local px0 executable against SHA-256 digests published with the upstream `v0.1.2` release. A binary that merely reports the correct version is not accepted.

On Linux, authoritative inspection fails closed unless `bubblewrap` (`bwrap`) is available. The sandbox does **not** expose the host root. It builds a minimal filesystem view containing only system runtime paths required by px0/Git, `/proc`, `/dev`, a private writable `/tmp`, the exact reviewed workspace, and any external Git worktree metadata required for that workspace. Candidate/Git mounts are read-only. The process starts with a sanitized environment rather than inheriting shell credentials or cloud tokens.

When px0 exits, RESIDUAL recomputes the snapshot. If HEAD/tree changed or the worktree became dirty, the session exits with status `3` and reports that the review became stale. A stale review must not be treated as approval evidence.

## Qualified px0 build

The integration currently pins:

- px0 version: `0.1.2`
- upstream release commit: `343c14a705b3021bd18ee521c82f7d7227c4ee88`
- upstream release SHA-256 values for supported OS/architecture artifacts

Residual refuses to launch a different version or an executable whose SHA-256 does not match the qualified upstream release artifact for the current platform.

For authoritative Linux review, install the authenticated px0 executable under a system runtime path; `/usr/local/bin/px0` is the recommended location. This lets the sandbox expose the executable without exposing the operator home directory.

The qualified `v0.1.2` build does not expose a `-no-telemetry` CLI flag. Residual therefore does not pass that nonexistent option. It launches with `DO_NOT_TRACK=1` / `PX0_TELEMETRY=0` in the sanitized environment, and redirects the build's automatic daily update check to loopback with `PX0_UPDATE_URL=http://127.0.0.1:9` so inspection does not make that outbound request.

## Usage

Install the official pinned px0 release artifact at `/usr/local/bin/px0` and, on Linux, install `bubblewrap`, then run:

```bash
residual inspector /path/to/clean/git/worktree
```

Useful options:

```bash
residual inspector . --no-open
residual inspector . --port 7777
residual inspector . --receipt /tmp/residual-inspection.json
residual inspector . --px0 /usr/local/bin/px0
```

Receipt paths **must be outside the reviewed workspace**. This is intentional: writing a receipt into the repository being reviewed would dirty the worktree and invalidate the snapshot binding.

The default policy intentionally uses:

- loopback only (`127.0.0.1`);
- OS-assigned port selection when `--port 0` is used; Residual reads px0's actual bound URL instead of guessing a free port;
- browser launch from the parent Residual process, while px0 itself always receives `-no-open`;
- language servers disabled (`-no-lsp`) unless explicitly enabled;
- a sanitized environment with operator secrets omitted;
- Linux `bubblewrap` minimal-filesystem isolation for authoritative review;
- Git awareness enabled against read-only workspace/Git metadata.

`--unsafe-no-sandbox` exists only for local browsing on systems where the secure backend is unavailable. The resulting receipt records `sandboxed: false` and is **non-authoritative**; it must not satisfy a policy requiring trusted human inspection evidence.

## Receipt

`--receipt` writes a JSON launch receipt with the bound Git snapshot and inspection-tool identity. Example fields:

```json
{
  "schema_version": 2,
  "tool": "px0",
  "tool_version": "0.1.2",
  "upstream_commit": "343c14a705b3021bd18ee521c82f7d7227c4ee88",
  "binary_sha256": "...",
  "binary_qualified": true,
  "workspace": "/absolute/path/to/worktree",
  "head_commit": "...",
  "tree_hash": "...",
  "url": "http://127.0.0.1:49152",
  "lsp_enabled": false,
  "telemetry_enabled": false,
  "sandboxed": true,
  "sandbox_backend": "bubblewrap",
  "launched_at": "..."
}
```

This receipt establishes what the operator inspected and the boundary under which it was inspected; it is not itself an approval or correctness certificate.

## Intended Station/Factory use

For a candidate worktree, launch the inspector against the already committed candidate revision. Human review can then use px0's code navigation, Git search, symbols, references, call trails, and Git-aware inspection while RESIDUAL remains the sole owner of review state and deterministic integration.
