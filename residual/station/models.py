"""BYO model roles, Ollama lifecycle, and resumable model-download UX."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict
from pathlib import Path

from residual.core import ContractError, canonical, strict_json
from residual.providers import HTTPProvider, NoRedirect, ProviderError

DEFAULTS = {
    "local": {"kind": "ollama", "model": "qwen2.5-coder:7b", "base_url": "http://127.0.0.1:11434", "placement": "local", "output_token_field": "max_tokens"},
    "cloud": {"kind": "openai_compatible", "model": "", "base_url": "", "placement": "remote", "output_token_field": "max_completion_tokens"},
    "review_placement": "local", "workers": 2, "max_output_tokens": 4096,
    "cloud_fallbacks": [], "local_failover": [], "observations_enabled": True,
    "batch_max_passes": 30, "batch_token_budget": 200000, "batch_wall_clock_s": 3600,
}
CATALOG = [
    {"name": "qwen2.5-coder:3b", "label": "Light runner", "download": "1.9 GB", "description": "Small, scoped edits. Lower memory footprint.", "url": "https://ollama.com/library/qwen2.5-coder:3b"},
    {"name": "qwen2.5-coder:7b", "label": "Code runner", "download": "4.7 GB", "description": "A starting point for implementation and local review.", "url": "https://ollama.com/library/qwen2.5-coder:7b"},
]
MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,150}$")


# Preserve the existing runner constructor while switching its implementation.
from residual.modular import ModularProvider, PROVIDERS, normalize_profile, make_adapter, normalized_usage
from ai_providers import Router, Registry, ChatRequest, Message, Role, ProviderError as ModularError
StationProvider = ModularProvider


def credentials_for(settings, kind, placement="cloud"):
    if placement == "local": return dict(settings.get("local_credentials", {}))
    values = dict(settings.get("provider_credentials", {}).get(kind, {}))
    if placement == "cloud" and kind == settings.get("cloud", {}).get("kind") and not values.get("api_key"):
        key = settings.get("cloud_key") or os.environ.get("RESIDUAL_CLOUD_API_KEY")
        if key: values["api_key"] = key
    return values


def model_call(store, pid, role, packet, system, schema=None, placement="local", tid=None, *, extensions=None):
    if placement not in {"local", "cloud"}: raise ContractError("Invalid model placement")
    settings = store.settings()
    primary = normalize_profile(settings.get(placement, DEFAULTS[placement]), "remote" if placement == "cloud" else "local")
    profiles = [primary]
    if placement == "cloud":
        profiles += [normalize_profile(p, "remote") for p in settings.get("cloud_fallbacks", [])]
    reg = Registry()
    for profile in profiles:
        adapter = make_adapter(profile, credentials_for(settings, profile["kind"], placement))
        reg.register(profile["kind"], lambda a=adapter: a)
    candidates = [p["kind"] + ":" + p["model"] for p in profiles]
    if placement == "local": candidates += [primary["kind"] + ":" + m for m in settings.get("local_failover", [])]
    cap = settings.get("max_output_tokens", 4096)
    req = ChatRequest(primary["model"], (Message(Role.SYSTEM, system), Message(Role.USER, canonical(packet))), max_tokens=cap, response_schema=schema)
    def reserve(provider, request, meta):
        if pid: store.reserve_call(pid, role, primary["placement"], meta["request_bytes"], tid)
    def receipt(value):
        if pid:
            usage = normalized_usage(value["usage"])
            store.event(pid, "usage.recorded", {"role":role, "placement":placement, "model":value["model"], "provider":value["provider"],
                **asdict(usage), "request_bytes":value["request_bytes"], "elapsed_ms":value["elapsed_ms"], "status":value["status"],
                "request_id":value["request_id"], "provider_attempt":value["attempt"], "error":value["error"]}, tid)
    router = Router(registry=reg, default_provider=primary["kind"], observation_bus=store.observation_bus(pid, role=role, placement=placement, task=tid or ""),
                    before_attempt=reserve, after_attempt=receipt)
    start = time.monotonic()
    from residual.quarantine import ProposedAction, QuarantineStore, PolicyDecision
    from residual.core import digest
    bus = store.observation_bus(pid, role=role, placement=placement, task=tid or "")
    quarantine = QuarantineStore(emit=(lambda event, data: bus.emit("custom", {"event": event, **data}, source="residual.quarantine")) if bus else None)
    held = quarantine.hold(ProposedAction("provider_call", primary["kind"],
        {"packet_sha256": digest(packet), "max_output_tokens": cap, "candidates": candidates,
         "payload": packet}, agent_id=role))
    def sharing_policy(action):
        if pid and placement == "cloud" and not store.project(pid)["allow_cloud"]:
            return "cloud_sharing_disabled"
        return None
    policies = (sharing_policy,) + (extensions.policies() if extensions is not None else ())
    if quarantine.evaluate(held, policies) == PolicyDecision.DENY:
        quarantine.deny(held, "provider_policy_denied", "provider_policies")
        if sharing_policy(held.action) is not None:
            raise ContractError("Cloud sharing is disabled for this project")
        raise ContractError("Provider call blocked by sharing or extension policy")
    reply = quarantine.release(held, lambda _: router.chat(candidates[0], req, failover=candidates[1:]), raise_errors=True).result
    if schema:
        if reply.finish_reason == "length": raise ContractError("Model output was truncated. Narrow the task or increase the output limit.")
        if reply.finish_reason in {"content_filter", "error", "unknown"} or reply.tool_calls: raise ContractError("Model did not complete a usable structured response")
        try: return strict_json(reply.content)
        except (ValueError, TypeError): raise ContractError("Model did not return valid JSON; choose a model with structured-output support") from None
    return {"text":reply.content, "usage":asdict(normalized_usage(reply.usage)), "elapsed_ms":round((time.monotonic()-start)*1000)}


def save_settings(store, incoming):
    allowed = {"local", "cloud", "cloud_key", "clear_cloud_key", "review_placement", "workers", "max_output_tokens",
               "provider_credentials", "local_credentials", "cloud_fallbacks", "local_failover", "observations_enabled",
               "batch_max_passes", "batch_token_budget", "batch_wall_clock_s"}
    if not isinstance(incoming, dict) or set(incoming) - allowed: raise ContractError("Unsupported setting")
    current = store.settings(); clean = {}; secrets = dict(current.get("provider_credentials", {}))
    # Bind a legacy key to its original provider before a route is changed.
    oldkind = current.get("cloud", DEFAULTS["cloud"])["kind"]
    if current.get("cloud_key"): secrets[oldkind] = {**secrets.get(oldkind, {}), "api_key":current["cloud_key"]}
    fields = {"kind", "model", "base_url", "output_token_field", "region", "api_version"}
    for placement in ("local", "cloud"):
        if placement not in incoming: continue
        p = incoming[placement]
        if not isinstance(p,dict) or set(p)-fields: raise ContractError("Unsupported model profile field")
        if placement=="cloud" and not p.get("model") and not p.get("base_url"):
            clean[placement]=dict(DEFAULTS["cloud"]); continue
        clean[placement]=normalize_profile(
            p,
            "remote" if placement=="cloud" else "local",
            allow_empty_model=(placement=="cloud" and p.get("kind")=="arena"),
        )
    if "cloud_fallbacks" in incoming:
        fallbacks = incoming["cloud_fallbacks"]
        if not isinstance(fallbacks,list) or len(fallbacks)>3 or any(not isinstance(p,dict) or set(p)-fields for p in fallbacks): raise ContractError("Use at most three cloud fallback profiles")
        clean["cloud_fallbacks"]=[normalize_profile(p,"remote") for p in fallbacks]
    combined = {**current, **clean}
    profiles = [combined.get("cloud",DEFAULTS["cloud"])] + combined.get("cloud_fallbacks",[])
    kinds = [p["kind"] for p in profiles]
    if len(kinds)!=len(set(kinds)): raise ContractError("Use one profile per cloud provider; fallback providers must be distinct")
    if "local_failover" in incoming:
        models=incoming["local_failover"]
        if not isinstance(models,list) or len(models)>3 or len(set(models))!=len(models): raise ContractError("Use at most three distinct local fallback model IDs")
        local=combined.get("local",DEFAULTS["local"])
        for model in models: normalize_profile({**local,"model":model},"local")
        if local["model"] in models: raise ContractError("A local fallback must differ from the primary model")
        clean["local_failover"]=models
    for name,low,high in (("workers",1,8),("max_output_tokens",256,16000),
                          ("batch_max_passes",1,300),("batch_token_budget",1,10000000),("batch_wall_clock_s",1,86400)):
        if name in incoming:
            value=incoming[name]
            if type(value) is not int or not low<=value<=high: raise ContractError(f"{name} must be {low}–{high}")
            clean[name]=value
    if "observations_enabled" in incoming:
        if type(incoming["observations_enabled"]) is not bool: raise ContractError("Observation recording must be a boolean")
        clean["observations_enabled"]=incoming["observations_enabled"]
    if "review_placement" in incoming:
        if incoming["review_placement"] not in {"local","cloud"}: raise ContractError("Review placement must be local or cloud")
        clean["review_placement"]=incoming["review_placement"]
    edits=incoming.get("provider_credentials",{})
    if not isinstance(edits,dict) or set(edits)-set(PROVIDERS): raise ContractError("Unknown credential provider")
    edits={k:dict(v) if isinstance(v,dict) else v for k,v in edits.items()}
    kind=combined.get("cloud",DEFAULTS["cloud"])["kind"]
    if incoming.get("clear_cloud_key"): edits.setdefault(kind,{})["clear"]=True
    elif incoming.get("cloud_key"): edits.setdefault(kind,{})["api_key"]=incoming["cloud_key"]
    for kind,values in edits.items():
        permitted={"access_key","secret_key","session_token","clear"} if kind=="bedrock" else {"api_key","clear"}
        if not isinstance(values,dict) or set(values)-permitted: raise ContractError("Unsupported credential field")
        if "clear" in values and type(values["clear"]) is not bool: raise ContractError("Credential removal must be boolean")
        secret={} if values.get("clear") else dict(secrets.get(kind,{}))
        for key,value in values.items():
            if key=="clear" or value=="": continue
            if not isinstance(value,str) or len(value)>10000 or any(ord(c)<32 for c in value): raise ContractError("Invalid credential")
            secret[key]=value
        secrets[kind]=secret
    if "local_credentials" in incoming:
        values=incoming["local_credentials"]
        if not isinstance(values,dict) or set(values)-{"api_key","clear"}: raise ContractError("Invalid local credentials")
        secret={} if values.get("clear") else dict(current.get("local_credentials",{}))
        if values.get("api_key"):
            key=values["api_key"]
            if not isinstance(key,str) or len(key)>10000 or any(ord(c)<32 for c in key): raise ContractError("Invalid local API key")
            secret["api_key"]=key
        clean["local_credentials"]=secret
    clean["provider_credentials"]=secrets
    clean["cloud_key"]=""  # legacy values are migrated into provider-scoped credentials
    store.settings(clean)


def public_settings(store):
    s=store.settings()
    from residual.modular import ENV_KEYS
    credentials={kind:{"saved":bool(credentials_for(s,kind)), "environment":bool(os.environ.get(ENV_KEYS.get(kind,'')) or (kind=="bedrock" and os.environ.get("AWS_ACCESS_KEY_ID")))} for kind in PROVIDERS}
    return {**{k:s.get(k,v) for k,v in DEFAULTS.items()}, "has_cloud_key":bool(credentials_for(s,s.get("cloud",DEFAULTS["cloud"])["kind"])),
            "credential_status":credentials, "has_local_key":bool(s.get("local_credentials") or os.environ.get("RESIDUAL_LOCAL_API_KEY")), "providers":PROVIDERS}


class Ollama:
    def __init__(self, store):
        self.store = store
        self.process = None
        self.log_handle = None

    def base(self):
        p = self.store.settings().get("local", DEFAULTS["local"])
        if p["kind"] != "ollama":
            return "http://127.0.0.1:11434"
        HTTPProvider("ollama", "check", p["base_url"], "local")
        return p["base_url"].rstrip("/")

    def request(self, path, body=None, timeout=5):
        req = urllib.request.Request(self.base() + path, data=canonical(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        return opener.open(req, timeout=timeout)

    def binary(self):
        exe = "ollama.exe" if os.name == "nt" else "ollama"
        root = self.store.root / "runtime"
        for p in (root / "bin" / exe, root / exe):
            if p.is_file():
                return str(p)
        return shutil.which("ollama")

    def status(self):
        info = {"connected": False, "installed": bool(self.binary()), "managed": self.process is not None and self.process.poll() is None,
                "models": [], "running": [], "platform": platform.system(), "catalog": CATALOG,
                "disk_free_gb": round(shutil.disk_usage(self.store.root).free / 1024**3, 1), "cpu_count": os.cpu_count()}
        try:
            with self.request("/api/tags") as response:
                info["models"] = json.loads(response.read(1_000_000)).get("models", [])
            info["connected"] = True
            with self.request("/api/ps") as response:
                info["running"] = json.loads(response.read(1_000_000)).get("models", [])
        except (OSError, ValueError, ProviderError):
            pass
        return info

    def start(self):
        if self.status()["connected"]:
            return "Ollama is already running"
        binary = self.binary()
        if not binary:
            raise ContractError("Install the local runtime first, or use the bundled Docker launcher")
        from urllib.parse import urlsplit
        env = {**os.environ, "OLLAMA_HOST": urlsplit(self.base()).netloc, "OLLAMA_MODELS": str(self.store.root / "models"), "OLLAMA_NO_CLOUD": "1"}
        self.log_handle = open(self.store.root / "ollama.log", "ab")
        self.process = subprocess.Popen([binary, "serve"], env=env, stdout=self.log_handle, stderr=self.log_handle)
        return "Ollama is starting. Refresh connection status in a moment."

    def stop(self):
        if not self.process or self.process.poll() is not None:
            raise ContractError("This station only stops the Ollama process it started")
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        if self.log_handle:
            self.log_handle.close()

    def pull(self, name, progress):
        if not isinstance(name, str) or not MODEL_NAME.fullmatch(name) or ".." in name:
            raise ContractError("Enter a valid Ollama model tag")
        with self.request("/api/pull", {"model": name, "stream": True}, timeout=600) as response:
            for line in response:
                if len(line) > 100_000:
                    raise ContractError("Unexpected download response")
                item = json.loads(line)
                if "error" in item:
                    raise ContractError("Model download failed. Check the model tag, connectivity, and available disk space.")
                total, completed = item.get("total", 0), item.get("completed", 0)
                progress(str(item.get("status", "Downloading"))[:160], round(100 * completed / total) if total else None)
        return "Model downloaded; select it as the local runner"

    def unload(self, name):
        if not isinstance(name, str) or not MODEL_NAME.fullmatch(name):
            raise ContractError("Invalid model tag")
        with self.request("/api/generate", {"model": name, "keep_alive": 0, "stream": False}, timeout=30) as response:
            response.read(10000)

    def install(self, progress):
        """Fetch a pinned official binary; verify its published SHA-256 before extraction."""
        manifest = json.loads((Path(__file__).parent / "schemas" / "runtime.json").read_text())
        machine = platform.machine().lower()
        key = platform.system() + ("-arm64" if machine in {"arm64", "aarch64"} else "-amd64")
        asset = manifest["assets"].get(key)
        if not asset:
            raise ContractError("Use the Docker launcher or install Ollama from ollama.com/download for this platform")
        staging = self.store.root / "runtime-download"
        staging.mkdir(exist_ok=True)
        archive = staging / asset["name"]
        h = hashlib.sha256()
        req = urllib.request.Request(asset["url"], headers={"User-Agent": "Residual-Command-Station/0.2"})
        with urllib.request.urlopen(req, timeout=60) as response, archive.open("wb") as f:
            total = int(response.headers.get("Content-Length", "0")); done = 0
            while chunk := response.read(1024 * 1024):
                f.write(chunk); h.update(chunk); done += len(chunk)
                if done > 6_000_000_000:
                    raise ContractError("Runtime download exceeds 6 GB")
                progress("Downloading verified Ollama runtime", round(done * 100 / total) if total else None)
        if h.hexdigest() != asset["sha256"]:
            archive.unlink(missing_ok=True)
            raise ContractError("Runtime checksum mismatch; download discarded")
        dest = self.store.root / "runtime"
        dest.mkdir(exist_ok=True)
        progress("Extracting local runtime", None)
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as z:
                for item in z.infolist():
                    if not (dest / item.filename).resolve().is_relative_to(dest.resolve()):
                        raise ContractError("Unsafe runtime archive member")
                z.extractall(dest)
        elif archive.name.endswith(".tar.zst"):
            # Official signed-content digest is checked above. GNU tar needs zstd on native Linux.
            if not shutil.which("zstd"):
                raise ContractError("Native Linux extraction requires zstd. Install zstd or use the included Docker launcher.")
            result = subprocess.run(["tar", "--zstd", "-xf", str(archive), "-C", str(dest)], capture_output=True, timeout=300)
            if result.returncode:
                raise ContractError("Could not extract runtime archive")
        else:
            with tarfile.open(archive) as t:
                t.extractall(dest, filter="data")
        if not self.binary():
            raise ContractError("Runtime extracted but the executable was not found")
        archive.unlink(missing_ok=True)
        return self.start()
