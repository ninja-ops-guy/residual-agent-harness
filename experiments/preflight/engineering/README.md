# Retained engineering preflight

`preflight-20260915.json` contains 16 successfully measured cases, one sample per
case, from the exact command in `docs/program/audit/README.md`. It includes the
controller, observability and accounting probes and SHA-256 fingerprints of
executed source files. Its source commit is the reviewed base; `worktree_dirty`
is explicitly true because this new harness and its documentation had not yet
been committed. The executed harness bytes are independently fingerprinted.

`source-inventory.json` records 25 pinned source files at main, PR40, PR43 and
PR81, with content hashes, symbol line ranges and source URLs.
`validation-20260915.json` retains the actual unittest command, output, exit
status, and hashes of its code and input evidence.

The completed engineering dimensions were 10/100/1,000 synthetic scheduler node
records; 1k/10k/100k in-memory observations; 100/1k/10k-node wide and chain plans;
10/1k receipt artifact bindings; and M2 captures of 10/100 files of 1 KiB each.
Every case stayed within its 10-second deadline. No maximum supported limit was
established, and no concurrent workers were launched.

The source algorithm repeatedly scans unresolved DAG dependencies. The retained
10k-node chain case took about 2.13 seconds while its wide counterpart took
about 0.11 seconds on this shared host. This is an engineering signal for future
profile-driven optimization, not a throughput guarantee or reliability result.
Do not compare these single warm-process samples as statistical performance
estimates. M4 sandbox startup, output limits and accepted integration are
explicitly unmeasured until the #81 boundary is qualified.

The controller fixture proves a feedback path from swarm to single for the
chosen synthetic overhead input. Its assigned seconds and success flags are
not benchmark data. The report also retains unfixed defects from pinned PR40/43;
the tests intentionally reproduce those findings without editing those branches.

These files must not enter confirmatory R0–R5, degradation, heterogeneous swarm,
or paper reliability datasets. There were zero model calls.
