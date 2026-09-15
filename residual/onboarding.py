"""First-run setup and diagnostics for managed FreeLLMAPI capacity.

The onboarding layer is deliberately stdlib-only. It owns local service lifecycle
and credential bootstrapping; normal inference still flows through Residual's
existing hardened OpenAI-compatible provider transport.
"""
from __future__ import annotations

import getpass
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path

from .providers import HTTPProvider, ProviderError


# v0.9.9 / sha-780a7d8. Pin the container by immutable digest so onboarding
# cannot silently execute a different upstream image under a mutable tag.
FREELLMAPI_IMAGE = (
    "ghcr.io/tashfeenahmed/freellmapi@"
    "sha256:d841398467798ec1e8577204d40b9ed354e5035b74f573636d0eca4bf2fac2b3"
)
DEFAULT_ENDPOINT = "http://127.0.0.1:3001/v1"
MANAGED_KEY_ENV = "RESIDUAL_FREELLMAPI_KEY"


@dataclass(frozen=True)
class ProviderManifest:
    id: str
    name: str
    platform: str
    signup_url: str
    key_hint: str
    recommended_for: tuple[str, ...]


PROVIDERS = {
    "groq": ProviderManifest(
        "groq", "Groq", "groq", "https://console.groq.com/keys",
        "Create an API key in the Groq console.", ("fast workers", "low-cost burst capacity"),
    ),
    "google": ProviderManifest(
        "google", "Google AI Studio", "google", "https://aistudio.google.com/app/apikey",
        "Create a Gemini API key in Google AI Studio.", ("broad model access", "fallback capacity"),
    ),
    "cerebras": ProviderManifest(
        "cerebras", "Cerebras", "cerebras", "https://cloud.cerebras.ai/",
        "Create an API key in Cerebras Cloud.", ("very fast workers", "batch capacity"),
    ),
    "mistral": ProviderManifest(
        "mistral", "Mistral", "mistral", "https://console.mistral.ai/api-keys/",
        "Create an API key in the Mistral console.", ("general workers", "fallback capacity"),
    ),
    "openrouter": ProviderManifest(
        "openrouter", "OpenRouter", "openrouter", "https://openrouter.ai/settings/keys",
        "Create an API key in OpenRouter.", ("model diversity", "continuity"),
    ),
}


@dataclass(frozen=True)
class ManagedPaths:
    home: Path

    @classmethod
    def from_value(cls, value: str | Path | None = None) -> "ManagedPaths":
        raw = Path(value).expanduser() if value else Path(os.environ.get("RESIDUAL_HOME", "~/.residual")).expanduser()
        return cls(raw.resolve())

    @property
    def service_dir(self) -> Path:
        return self.home / "services" / "freellmapi"

    @property
    def compose(self) -> Path:
        return self.service_dir / "compose.yaml"

    @property
    def service_env(self) -> Path:
        return self.service_dir / ".env"

    @property
    def config(self) -> Path:
        return self.home / "config.toml"

    @property
    def secrets_env(self) -> Path:
        return self.home / "secrets.env"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    fixable: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


COMPOSE = f'''services:
  freellmapi:
    image: {FREELLMAPI_IMAGE}
    restart: unless-stopped
    ports:
      - "${{HOST_BIND:-127.0.0.1}}:${{PORT:-3001}}:3001"
    environment:
      ENCRYPTION_KEY: "${{ENCRYPTION_KEY}}"
      PORT: "3001"
      FREEAPI_CONFIG_JSON: "${{FREEAPI_CONFIG_JSON:-}}"
    volumes:
      - freellmapi-data:/app/server/data

volumes:
  freellmapi-data:
'''


def _chmod_private(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _atomic_private_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    _chmod_private(tmp)
    tmp.replace(path)
    _chmod_private(path)


def _run(command: list[str], *, cwd: Path | None = None, env: dict | None = None,
         timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=timeout, check=False,
    )


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    result = _run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=15)
    return result.returncode == 0


def compose_available() -> bool:
    if not shutil.which("docker"):
        return False
    result = _run(["docker", "compose", "version"], timeout=15)
    return result.returncode == 0


def ensure_service_files(paths: ManagedPaths) -> bool:
    """Create Residual-owned FreeLLMAPI service files without overwriting secrets."""
    paths.service_dir.mkdir(parents=True, exist_ok=True)
    changed = False
    if not paths.compose.exists() or paths.compose.read_text(encoding="utf-8") != COMPOSE:
        paths.compose.write_text(COMPOSE, encoding="utf-8")
        changed = True
    if not paths.service_env.exists():
        encryption_key = secrets.token_hex(32)
        _atomic_private_write(
            paths.service_env,
            f"ENCRYPTION_KEY={encryption_key}\nPORT=3001\nHOST_BIND=127.0.0.1\n",
        )
        changed = True
    else:
        _chmod_private(paths.service_env)
    return changed


def _stop_bootstrap_container(paths: ManagedPaths, clean_env: dict[str, str]) -> None:
    """Best-effort fail-closed cleanup when a credential scrub cannot be proven."""
    _run(["docker", "compose", "down", "--remove-orphans"],
         cwd=paths.service_dir, env=clean_env, timeout=60)


def start_service(paths: ManagedPaths, bootstrap: dict | None = None) -> tuple[bool, str]:
    if not docker_available():
        return False, "docker daemon unavailable"
    if not compose_available():
        return False, "docker compose unavailable"
    ensure_service_files(paths)
    env = os.environ.copy()
    if bootstrap:
        env["FREEAPI_CONFIG_JSON"] = json.dumps(bootstrap, separators=(",", ":"))
    result = _run(["docker", "compose", "up", "-d"], cwd=paths.service_dir, env=env)
    if result.returncode != 0:
        return False, "docker compose start failed"
    if bootstrap:
        # Bootstrap is deliberately temporary: regardless of readiness outcome,
        # recreate the service without FREEAPI_CONFIG_JSON. If we cannot prove
        # that recreation succeeded, stop/remove the service so a container
        # carrying the plaintext upstream credential is not left running.
        imported_ready = wait_for_http("http://127.0.0.1:3001/", timeout=45)
        clean = os.environ.copy()
        clean.pop("FREEAPI_CONFIG_JSON", None)
        scrub = _run(
            ["docker", "compose", "up", "-d", "--force-recreate"],
            cwd=paths.service_dir, env=clean,
        )
        if scrub.returncode != 0:
            _stop_bootstrap_container(paths, clean)
            return False, "credential scrub failed; managed service stopped"
        if not imported_ready:
            return False, "provider bootstrap did not become ready; credential scrubbed"
    return True, "running"


def wait_for_http(url: str, timeout: int = 30, headers: dict | None = None) -> bool:
    """Check service reachability; any non-5xx HTTP response proves a listener exists."""
    deadline = time.monotonic() + timeout
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        request = urllib.request.Request(url, headers=headers or {}, method="GET")
        try:
            with opener.open(request, timeout=3) as response:
                if 200 <= response.status < 500:
                    return True
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    return False


def endpoint_ready(api_key: str | None = None) -> bool:
    """Require successful authentication for the OpenAI-compatible model endpoint."""
    headers = {"Authorization": "Bearer " + api_key} if api_key else {}
    request = urllib.request.Request(DEFAULT_ENDPOINT + "/models", headers=headers, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=4) as response:
            return 200 <= response.status < 300
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return False


def _toml_string(value: str | Path) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def write_managed_config(paths: ManagedPaths, model: str = "auto") -> None:
    if not isinstance(model, str) or not model.strip() or any(c in model for c in "\r\n\""):
        raise ValueError("invalid model name")
    secret_path = _toml_string(paths.secrets_env)
    cache_path = _toml_string(paths.home / "cache.sqlite")
    config = f'''# Generated by `residual setup`. Secrets stay in the private env file.
[secrets]
env_file = "{secret_path}"

[local]
kind = "disabled"

[expert]
kind = "openai_compatible"
model = "{model}"
base_url = "{DEFAULT_ENDPOINT}"
# The proxy listener is local, but inference leaves the host for the selected
# upstream provider. Classify it as remote so local-only obligations and remote
# evidence filtering remain enforced by Residual's routing policy.
placement = "remote"
api_key_env = "{MANAGED_KEY_ENV}"
output_token_field = "max_tokens"
json_mode = true
timeout_seconds = 90

[limits]
local_rounds = 1

[cache]
enabled = true
path = "{cache_path}"
'''
    paths.home.mkdir(parents=True, exist_ok=True)
    paths.config.write_text(config, encoding="utf-8")


def write_unified_key(paths: ManagedPaths, key: str) -> None:
    key = key.strip()
    if not key or "\n" in key or "\r" in key:
        raise ValueError("invalid unified API key")
    _atomic_private_write(paths.secrets_env, f"{MANAGED_KEY_ENV}={key}\n")


def read_managed_key(paths: ManagedPaths) -> str | None:
    if not paths.secrets_env.exists():
        return None
    prefix = MANAGED_KEY_ENV + "="
    for line in paths.secrets_env.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip() or None
    return None


def smoke_test(api_key: str, model: str = "auto") -> tuple[bool, str]:
    """Exercise Residual's real HTTPProvider against the configured proxy."""
    provider = HTTPProvider(
        kind="openai_compatible", model=model, base_url=DEFAULT_ENDPOINT,
        placement="remote", api_key_env=MANAGED_KEY_ENV, output_token_field="max_tokens",
        timeout_seconds=45,
    )
    old = os.environ.get(MANAGED_KEY_ENV)
    os.environ[MANAGED_KEY_ENV] = api_key
    try:
        reply = provider.generate(
            {"smoke_test": True, "obligations": [], "instruction": "Return empty updates and requests."},
            96,
        )
        payload = json.loads(reply.text)
        if not isinstance(payload, dict) or set(payload) != {"updates", "requests"}:
            return False, "provider replied but did not satisfy the Residual worker contract"
        if not isinstance(payload["updates"], dict) or not isinstance(payload["requests"], list):
            return False, "provider reply failed worker contract types"
        return True, f"worker contract passed in {reply.elapsed_ms:.0f} ms"
    except (ProviderError, ValueError, TypeError):
        return False, "provider smoke test failed"
    finally:
        if old is None:
            os.environ.pop(MANAGED_KEY_ENV, None)
        else:
            os.environ[MANAGED_KEY_ENV] = old


def doctor(paths: ManagedPaths, fix: bool = False) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check(
        "python", "ok" if sys.version_info >= (3, 11) else "fail",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    ))

    docker_ok = docker_available()
    checks.append(Check(
        "docker", "ok" if docker_ok else "fail",
        "daemon reachable" if docker_ok else "Docker is not installed or the daemon is stopped",
    ))
    compose_ok = compose_available()
    checks.append(Check(
        "docker-compose", "ok" if compose_ok else "fail",
        "available" if compose_ok else "Docker Compose v2 is unavailable",
    ))

    files_ok = paths.compose.exists() and paths.service_env.exists()
    if not files_ok and fix:
        ensure_service_files(paths)
        files_ok = True
    checks.append(Check(
        "freellmapi-service", "ok" if files_ok else "warn", str(paths.service_dir), fixable=not files_ok,
    ))

    root_ready = wait_for_http("http://127.0.0.1:3001/", timeout=2)
    if not root_ready and fix and docker_ok and compose_ok:
        ok, _ = start_service(paths)
        root_ready = ok and wait_for_http("http://127.0.0.1:3001/", timeout=20)
    checks.append(Check(
        "freellmapi-http", "ok" if root_ready else "warn",
        "http://127.0.0.1:3001" if root_ready else "service not reachable",
        fixable=not root_ready and docker_ok and compose_ok,
    ))

    key = read_managed_key(paths)
    checks.append(Check(
        "unified-api-key", "ok" if key else "warn",
        "configured" if key else f"missing from {paths.secrets_env}",
    ))

    config_ok = paths.config.exists()
    if not config_ok and fix:
        write_managed_config(paths)
        config_ok = True
    checks.append(Check(
        "residual-config", "ok" if config_ok else "warn", str(paths.config), fixable=not config_ok,
    ))

    if key and root_ready:
        api_ok = endpoint_ready(key)
        checks.append(Check(
            "freellmapi-auth", "ok" if api_ok else "fail",
            "model catalog reachable" if api_ok else "unified key rejected or model endpoint unavailable",
        ))
    else:
        checks.append(Check("freellmapi-auth", "skip", "requires running service and unified key"))
    return checks


def print_doctor(checks: list[Check]) -> None:
    glyph = {"ok": "✓", "warn": "!", "fail": "✗", "skip": "○"}
    print("Residual System Diagnostic")
    print("─" * 36)
    for check in checks:
        print(f"{glyph.get(check.status, '?')} {check.name:<20} {check.detail}")
    failed = sum(c.status == "fail" for c in checks)
    warned = sum(c.status == "warn" for c in checks)
    if failed:
        print("\nRESULT: NOT READY")
    elif warned:
        print("\nRESULT: SETUP INCOMPLETE")
    else:
        print("\nRESULT: READY")


def list_providers() -> None:
    print("FreeLLMAPI upstream providers")
    print("─" * 36)
    for manifest in PROVIDERS.values():
        print(f"{manifest.id:<12} {manifest.name:<18} {', '.join(manifest.recommended_for)}")
        print(f"{'':12} {manifest.signup_url}")


def _choose_provider() -> ProviderManifest:
    manifests = list(PROVIDERS.values())
    print("\nChoose an upstream provider:")
    for index, manifest in enumerate(manifests, start=1):
        print(f"  {index}. {manifest.name:<18} {', '.join(manifest.recommended_for)}")
    while True:
        value = input("Select [1]: ").strip() or "1"
        if value.isdigit() and 1 <= int(value) <= len(manifests):
            return manifests[int(value) - 1]
        print("Choose one of the listed numbers.")


def setup(paths: ManagedPaths, provider_id: str | None = None, provider_key_env: str | None = None,
          unified_key_env: str | None = None, model: str = "auto", non_interactive: bool = False,
          skip_start: bool = False, skip_smoke: bool = False) -> int:
    print("Residual First-Run Setup")
    print("═" * 36)
    print(f"Managed home: {paths.home}")

    ensure_service_files(paths)
    manifest = PROVIDERS.get(provider_id) if provider_id else None
    upstream_key = None

    if provider_id and manifest is None:
        print(f"Unknown provider: {provider_id}", file=sys.stderr)
        return 1
    if manifest is None and not non_interactive:
        manifest = _choose_provider()

    if manifest:
        print(f"\n{manifest.name}: {manifest.signup_url}")
        print(manifest.key_hint)
        if provider_key_env:
            upstream_key = os.environ.get(provider_key_env)
            if not upstream_key:
                print(f"Environment variable {provider_key_env} is empty.", file=sys.stderr)
                return 1
        elif not non_interactive:
            upstream_key = getpass.getpass(
                f"{manifest.name} API key (Enter to configure in dashboard instead): "
            ).strip() or None

    bootstrap = None
    if manifest and upstream_key:
        bootstrap = {
            "keys": [{"platform": manifest.platform, "key": upstream_key, "label": "residual-bootstrap"}],
            "routing": {"strategy": "balanced"},
        }

    if not skip_start:
        print("\nStarting FreeLLMAPI...")
        ok, detail = start_service(paths, bootstrap)
        if not ok:
            print(f"✗ {detail}", file=sys.stderr)
            print(f"Run `residual doctor --fix --home {paths.home}` after Docker is available.")
            return 1
        if not wait_for_http("http://127.0.0.1:3001/", timeout=45):
            print("✗ FreeLLMAPI did not become reachable.", file=sys.stderr)
            return 1
        print("✓ FreeLLMAPI reachable at http://127.0.0.1:3001")

    write_managed_config(paths, model=model)
    print(f"✓ Residual config written to {paths.config}")

    unified_key = os.environ.get(unified_key_env) if unified_key_env else None
    if unified_key_env and not unified_key:
        print(f"Environment variable {unified_key_env} is empty.", file=sys.stderr)
        return 1

    if not unified_key and not non_interactive and not skip_start:
        print("\nFreeLLMAPI uses one unified key for clients.")
        print("Open http://127.0.0.1:3001 and copy the unified key from the Keys page header.")
        try:
            webbrowser.open("http://127.0.0.1:3001")
        except Exception:
            pass
        unified_key = getpass.getpass("Unified FreeLLMAPI key (Enter to finish later): ").strip() or None

    if unified_key:
        write_unified_key(paths, unified_key)
        print(f"✓ Unified key stored in private file {paths.secrets_env}")
        if not skip_smoke and not skip_start:
            ok, detail = smoke_test(unified_key, model=model)
            print(("✓ " if ok else "! ") + detail)
            if not ok:
                print("Setup completed, but the live worker smoke test needs attention.")
                return 2
    else:
        print("! Unified key not configured yet.")
        print("  Re-run setup with --unified-key-env, or add it to the private secrets file:")
        print(f"  {MANAGED_KEY_ENV}=freellmapi-...")

    print("\nSetup complete.")
    print(f"Run: residual doctor --home {paths.home}")
    print(f"Config: {paths.config}")
    return 0
