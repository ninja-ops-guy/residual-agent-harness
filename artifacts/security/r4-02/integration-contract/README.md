# R4-02 runtime integration reconciliation

Original security head: `ff410b5fb8695104f1dc78ffae7cc78199e15da9`; tree `ab16aa6b7afb58ab602c3e54a1e7c4c48a406c45`. Original CI and local BLOCKED records remain unchanged. This successor changes runtime environments only; no product/security source, floor, or test assertion changes.

`pre-change-proof.json` binds the Windows/macOS logs showing setup-python selected cached 3.12.10 and pip rejected Requires-Python before lifecycle execution. `runtime-matrix.json` inventories tracked selectors, inherited interpreters, embedded images, and fixtures. No explicitly pinned 3.12.10 runtime was found: both lifecycle jobs used the broad `3.12` constraint. Pages' 3.11.2 came from Debian Bookworm apt. Station's distro 3.12.3 was also below the numeric support contract despite Ubuntu backports.

Windows/macOS now use upstream 3.13.15 native builds. Pages retains linux/386, Bookworm, and the 3.11 minor using the official 3.11.16 slim image; its diagnostic file hashes follow the upstream `/usr/local` installation. Station retains Ollama 0.34.0's Ubuntu base/native libraries, copies the official Bookworm Python 3.12.14 installation (built against older glibc), and installs its runtime libraries. Both image builds invoke the unchanged extraction runtime guard; Station also imports its TLS, SQLite, compression, readline and ctypes dependencies.

The static qualification uses the existing unchanged pyproject Requires-Python specification. The native lifecycle transition and both container builds require fresh exact-head CI. Docker is unavailable in this WSL distro, so local validation is static plus relevant Python tests; no local image-build success is claimed.

Existing Linux jobs retain their passing minor-version coverage. Coarse selectors can still choose a stale cache, but package installation remains fail-closed. Independent Debian syscall controls do not install/import RESIDUAL and remain historical controls, not qualified runtimes. Test rejection fixtures and historical version observations are unchanged. Untracked Gemma setup files are user work and excluded from this tracked-selector inventory.

PR Agent is separate advisory automation: the original run failed after diff-budget pruning, with no definitive root cause recorded. It supplies no security or independent-review acceptance. No advisory accommodation is made.

Provider sources: [Actions Python build manifest](https://github.com/actions/python-versions/blob/main/versions-manifest.json), [official Python container inventory](https://github.com/docker-library/official-images/blob/master/library/python), and [Ollama 0.34.0 base](https://github.com/ollama/ollama/blob/v0.34.0/Dockerfile). Captured source SHA-256 hashes and selected build platforms are in `provider-selection.json`.

No merge or ready-for-review authorization. R4-03 remains stopped.

Concurrent PR work is preserved in ancestry: `ef17c0bf`, `898f8e68`, `bafac690`. The initial local commit `b235e0b7` was never pushed (fast-forward rejection). This successor reapplies its validated environment state on top of `bafac690`; it pins that head's 3.13 lifecycle selector and chooses patched Python3.11/Bookworm over its intermediate Trixie VM. See `concurrent-reconciliation.json`.
