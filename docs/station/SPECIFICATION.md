# Markdown specification format

Each mission contains prose plus exactly one fenced `json` or `ldd` block. JSON inside Markdown avoids ambiguous parsing and extra runtime dependencies. The UI includes a working template and a model-assisted draft generator.

```json
{
  "schema_version": 1,
  "name": "Service heartbeat",
  "goal": "Provide stable health state for the operations dashboard.",
  "tasks": [
    {
      "id": "OPS-001",
      "title": "Implement health state",
      "instruction": "Implement status(services), returning ready for a nonempty mapping of healthy services, otherwise degraded.",
      "depends_on": [],
      "route": "local",
      "files": ["health.py"],
      "context": [],
      "checks": [
        {"kind": "python_compile", "path": "health.py"},
        {"kind": "command", "argv": ["{python}", "-c", "from health import status; assert status({}) == 'degraded'; assert status({'db': True}) == 'ready'"], "timeout": 30}
      ]
    }
  ]
}
```

| Field | Contract |
|---|---|
| `schema_version` | Integer 1 |
| `name`, `goal` | Human-readable title and intended outcome |
| `tasks` | 1–100 tasks |
| `id` | Unique identifier beginning with a letter, up to 64 letters/digits/underscores/hyphens |
| `instruction` | Bounded implementation requirement |
| `files` | Explicit writable file list; no globs, deletion, or implicit repository-wide access |
| `context` | Additional read-only files supplied to the runner |
| `depends_on` | Tasks that must be integrated before assignment |
| `route` | `local` or `cloud`; cloud requires project permission |
| `checks` | At least one deterministic acceptance check |

Checks support `exists`, `contains` with a `text` field, `python_compile`, `json_valid`, and `command` with an argument array and optional 1–300 second timeout. `{python}` resolves to the station interpreter. Command checks require project opt-in. Shell syntax is not expanded.

The proposal contract creates/replaces complete text files. It does not edit binary assets, delete files, execute model-authored shell commands, or browse the repository automatically. Source files are limited to 80 KB each and 100 KB per supplied context; proposals are limited to 200 KB. Split large tasks and declare relevant interfaces in `context`.

Unknown fields, duplicate JSON keys, non-finite numbers, dependency cycles, unknown dependencies, protected paths and path traversal are rejected. Existing repositories must be clean and committed. Candidates are built in a separate managed copy.

The original spec is immutable for a mission. **Download Project Markdown** exports progress, structured state and the original specification. Editing that download does not change an active mission; explicitly import a revised mission.

Baseline checks may fail for unimplemented behavior. Candidate and accumulated integration checks must pass. Syntax validity is not a behavioral test; author checks that cover the actual requirement.
