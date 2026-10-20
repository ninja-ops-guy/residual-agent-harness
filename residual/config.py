"""TOML configuration; secrets remain outside the configuration document."""
import importlib
import os
import re
import stat
import tomllib
from pathlib import Path

from .core import ContractError, Registry, register_builtins
from .demo import DemoProvider, register as register_demo
from .engine import Harness, Limits
from .providers import HTTPProvider, Prices
from .storage import Cache


_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load_secret_env(spec, config_path: Path) -> None:
    """Load a private env file without placing secret values in TOML.

    Existing process environment always wins. On POSIX, group/world-readable
    files are rejected so managed credentials cannot silently become less safe.
    """
    if not isinstance(spec, dict) or set(spec) != {"env_file"} or not isinstance(spec.get("env_file"), str):
        raise ContractError("invalid secrets configuration")
    path = Path(spec["env_file"]).expanduser()
    if not path.is_absolute():
        path = config_path.parent / path
    try:
        info = path.stat()
    except OSError:
        raise ContractError("configured secrets file is unavailable") from None
    if not stat.S_ISREG(info.st_mode):
        raise ContractError("configured secrets path is not a file")
    if os.name != "nt" and stat.S_IMODE(info.st_mode) & 0o077:
        raise ContractError("configured secrets file permissions are too broad")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise ContractError("configured secrets file could not be read") from None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ContractError("invalid secrets env line")
        name, value = line.split("=", 1)
        if not _ENV_NAME.fullmatch(name):
            raise ContractError("invalid secrets environment variable name")
        os.environ.setdefault(name, value)


def load_config(path=None):
    if path is None:
        return {"local": {"kind": "demo", "role": "local"},
                "expert": {"kind": "demo", "role": "expert"},
                "limits": {"local_rounds": 1}, "cache": {"enabled": False}}
    config_path = Path(path).expanduser().resolve()
    with open(config_path, "rb") as file:
        data = tomllib.load(file)
    if set(data) - {"local", "expert", "limits", "plugins", "cache", "secrets"}:
        raise ContractError("unknown configuration sections")
    secrets_spec = data.pop("secrets", None)
    if secrets_spec is not None:
        _load_secret_env(secrets_spec, config_path)
    return data


def registry_from(config):
    registry = Registry()
    register_builtins(registry)
    register_demo(registry)
    for target in config.get("plugins", []):
        module, symbol = target.split(":", 1)
        getattr(importlib.import_module(module), symbol)(registry)
    return registry


def provider_from(spec, registry):
    if spec is None or spec.get("kind") == "disabled":
        return None
    spec = dict(spec)
    kind = spec.pop("kind")
    if kind == "demo":
        role = spec.pop("role", "local")
        if spec or role not in {"local", "expert"}:
            raise ContractError("invalid demo configuration")
        return DemoProvider(role)
    if kind in registry.providers:
        return registry.providers[kind](spec)
    prices = Prices(**spec.pop("prices")) if "prices" in spec else None
    from .modular import ModularProvider, PROVIDERS
    if kind in PROVIDERS:
        from .providers import SYSTEM, RESPONSE_SCHEMA
        key_env=spec.pop("api_key_env", None)
        timeout=spec.pop("timeout_seconds", 90)
        schema=RESPONSE_SCHEMA if spec.pop("json_mode", True) else None
        options=spec.pop("options", {})
        allowed={"model", "base_url", "placement", "output_token_field", "region", "api_version"}
        if set(spec)-allowed or options: raise ContractError("Unsupported modular provider option")
        if key_env and not os.environ.get(key_env): raise ContractError("Configured API key environment variable is missing")
        provider=ModularProvider({"kind":kind, **spec}, SYSTEM, schema, os.environ.get(key_env) if key_env else None)
        if type(timeout) not in (int,float) or not 0 < timeout <= 600: raise ContractError("Invalid provider timeout")
        provider.adapter.timeout=timeout
        provider.prices=prices
        return provider
    return HTTPProvider(kind=kind, prices=prices, **spec)


def build_harness(config, mode="residual", disable_cache=False):
    registry = registry_from(config)
    local, expert = provider_from(config.get("local"), registry), provider_from(config.get("expert"), registry)
    if local is None and expert is None:
        raise ContractError("configure at least one provider")
    cache_config = config.get("cache", {})
    if set(cache_config) - {"enabled", "path"} or type(cache_config.get("enabled", False)) is not bool:
        raise ContractError("invalid cache configuration")
    cache = None
    if cache_config.get("enabled", False) and not disable_cache:
        cache = Cache(cache_config.get("path", ".residual/cache.sqlite"))
    return Harness(registry, local, expert, Limits(**config.get("limits", {})), cache, mode)
