"""TOML configuration; secrets remain in environment variables."""
import importlib
import tomllib
from pathlib import Path

from .core import ContractError, Registry, register_builtins
from .demo import DemoProvider, register as register_demo
from .engine import Harness, Limits
from .providers import HTTPProvider, Prices
from .storage import Cache


def load_config(path=None):
    if path is None:
        return {"local": {"kind": "demo", "role": "local"},
                "expert": {"kind": "demo", "role": "expert"},
                "limits": {"local_rounds": 1}, "cache": {"enabled": False}}
    with open(path, "rb") as file:
        data = tomllib.load(file)
    if set(data) - {"local", "expert", "limits", "plugins", "cache"}:
        raise ContractError("unknown configuration sections")
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
        import os
        key_env=spec.pop("api_key_env", None)
        timeout=spec.pop("timeout_seconds", 90)
        schema=RESPONSE_SCHEMA if spec.pop("json_mode", True) else None
        options=spec.pop("options", {})
        allowed={"model", "base_url", "placement", "output_token_field", "region", "api_version", "gateway_allowed_routes", "gateway_allow_auto"}
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
