# Mission Control — chat-first real guest execution

Mission Control is the prompt-first public interface over the actual bundled RESIDUAL repository and Linux/WebVM guest. It is not a desktop simulation, a hosted SaaS backend, or a replacement for Factory/M4. The old `demo` command remains an explicitly scripted tutorial; the primary public experience is now the chat surface.

## Visitor workflow

1. Open `/demo/` and wait for `LINUX · READY`.
2. Use **Chat** as the primary surface. Enter a mission such as `Build a calculator` and send it.
3. Use the background tabs when you want detail:
   - **Activity** — provider state and the Mission / Workers / Verifiers / Integration / Policy projections.
   - **Evidence** — retained-ledger events, result binding, metrics, receipts and verifier scope.
   - **Files** — accepted generated files, downloads and the app preview.
   - **Terminal** — the same real Linux guest and repository used by Chat.
4. Builds and source-grounded prompts use **Connect provider**, which opens `/provider/` outside the cross-origin-isolated WebVM service-worker scope. Load Puter, sign in, leave the provider tab open, return to Chat, and explicitly authorize the mission.
5. Repository audit mode needs no model and operates directly on selected files in the guest.

There is no implicit scripted-model fallback for live/build missions. Provider/model/credit failures remain failures.

## Build mode and preview

`Build app / deliverable` creates a real RESIDUAL Task/Harness obligation. An accepted build is a bounded bundle of one to eight text files with safe relative paths. Files are saved only below:

```
runs/missions/<mission-id>/artifacts/
```

The manifest records hashes and `executed:false`. RESIDUAL does **not** automatically execute, deploy, merge or apply generated files to the repository, and a contract pass does not prove code correctness.

If an accepted bundle contains an HTML entry point, Mission Control automatically shows an **interactive browser preview** in the assistant response and the Files tab. Bundle-local JavaScript and CSS can run so a visitor can exercise the generated UI immediately. The preview uses an iframe without `allow-same-origin`, with `sandbox="allow-scripts"`; nested frames/objects/base/meta-refresh are stripped, external script/style references are removed, bundle-local script/style files are inlined, and a restrictive preview CSP disables connect/frame/object/form access and external resource loading.

This preview is a UX/runtime check, **not semantic verification and not a hardened multi-tenant execution sandbox**. Browser acceptance explicitly interacts with the generated calculator (`2 + 3 = 5`) while the retained RESIDUAL evidence still reports code correctness as UNKNOWN.

## Shared CLI

The terminal and chat use the same guest files:

```
mission build "Build a calculator" --config provider.toml --allow-cloud
mission audit --stream --files README.md residual/cli.py
mission inspect runs/missions/<mission-id>
python3 -m residual verify-trace runs/missions/<mission-id>/trace.jsonl --result runs/missions/<mission-id>/result.json
```

`mission` aliases the workbench CLI. A CLI audit with `--stream` projects its actual ledger back into Mission Control. Existing `residual run ... --config ...` remains available for custom tasks/providers.

## Architecture and trust boundaries

The UI writes a bounded mission JSON into a CheerpX DataDevice and invokes fixed Python module/argv combinations. User prompts, model text and file paths are not converted into shell commands. Source files are frozen before dispatch. Existing Harness acceptance and the existing hash-linked evidence ledger remain authoritative; browser UI events are projections, not a second trusted receipt chain.

Live provider responses use the RESIDUAL `updates` / `requests` worker protocol. The provider helper requests a `residual_submit` structured response where supported and validates the returned envelope before the guest accepts it. The guest then performs the real RESIDUAL checks. Mechanical build/source contracts do not establish answer truth or code correctness: **semantic correctness stays UNKNOWN** unless a stronger verifier establishes it.

No M4 trust-boundary implementation or shared evidence schema is changed by Mission Control.

## Provider and service limits

Puter authentication stays in the separate same-origin provider helper and credentials are not forwarded into the guest. Each browser mission explicitly grants a bounded model/call/token budget. Client/guest limits are not abuse-resistant service quotas: a user controlling their browser can modify them. Signup, durable hosted workspaces, server-enforced rate limits, concurrency admission, billing and abuse controls remain later backend work.

## Evidence / claim discipline

Browser qualification must boot the real Linux guest, run real Harness work, verify retained traces/results, exercise Chat/background tabs, generate calculator files and interact with the calculator preview. Provider output in CI is supplied by an explicit Playwright SDK test double. Therefore CI proves the guest/Harness/provider-transport/UI/preview contracts but **does not prove real Puter account login, paid model inference, Safari, or physical iOS/Android compatibility**. Those claims require separate retained evidence.
