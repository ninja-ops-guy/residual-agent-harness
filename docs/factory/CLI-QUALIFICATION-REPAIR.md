# Factory CLI qualification repair

Use `python -m residual.factory` for the Factory CLI. The package entry point
delegates to the existing runtime `main()` after package initialization.
Running the runtime submodule directly with `-m residual.factory.runtime`
can emit a `runpy` warning because package imports already load that submodule.
No warning is filtered or suppressed by the new entry point.

## Findings and limits

PR #109 at `91c9ae67` failed twice on Python 3.13 in the `--trace-id` subtest
of the lifecycle missing-input CLI check. The original logs retain the
JSONDecodeError but not the rejected document. The suite also emitted unclosed
SQLite ResourceWarnings. The instrumented full suite at `1e4c02c5` passed;
**that pass does not establish the historical failure's exact cause**.

Local adversarial reproduction establishes a concrete test defect: an
unrelated parent-process ResourceWarning can enter the old global stderr
capture and cause that same JSONDecodeError. A real subprocess also exposed
the separate deterministic `runpy` warning described above.

## Repair and validation

The existing protected lifecycle test now invokes the package CLI in a real
subprocess for both `--run-id` and `--trace-id`. It preserves all original
assertions: exit 1, empty stdout, exact blocked/FileNotFoundError JSON, no
fixture-path disclosure, and no journal attempts. It adds a 15-second process
timeout. No runtime, receipt, sandbox, deadline or acceptance logic changes.

`test_factory_cli_process_isolation.py` injects a parent ResourceWarning at
each invocation, verifies both injections occurred and remained visible in
the parent, and executes the existing assertions against the real child.
Restoring the old in-process capture causes this regression to fail with
JSONDecodeError. Local validation: 21 unittest cases; 21 pytest cases plus
22 subtests passed. Full fresh CI remains required for the published head.

## Independent review required

One protected file changes: `tests/test_factory_runtime_lifecycle.py`.
Its ownership pin has deliberately not been advanced. The ownership gate
must remain failing until independent review accepts the changed test,
the new entry point, and the mutation evidence, followed by an explicitly
reviewed baseline update. There is no metadata-only exception and no
self-approval. Any final candidate must receive fresh qualification.

## Retained evidence transport

The M4 workflow continues to upload its six normal evidence files. It also
uses read-only Actions access to retrieve that uploaded ZIP, checks its
SHA-256 against the upload action's digest, and emits bounded base64 chunks
in the job log. This permits byte-exact retention when the local artifact
download URL cannot be used. Repository credentials are never forwarded to
the storage redirect. The export requires exactly six unique expected filenames.
It bounds the ZIP to 1 MiB compressed and 16 MiB total declared uncompressed
content before emitting any bytes. Real ZIP regression fixtures reject every
missing member, duplicates, extra members, empty archives and excessive
expansion, and verify the inclusive size boundary. This is a transport check,
not an acceptance decision.

The ordinary unittest diagnostic wrapper preserves discovery, default
warning handling, failures and exit status. It only records a failed JSON
document for the named missing-input fixture; it does not collect arbitrary
test locals or environment values.
