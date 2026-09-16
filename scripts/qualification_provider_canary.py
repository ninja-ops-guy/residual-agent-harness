#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from ai_providers.core import ChatRequest, Message, Role

CANARY = "RESIDUAL_CANARY_OK"


def adapter(provider: str, api_key: str | None, base_url: str | None):
    if provider == "openai":
        from ai_providers.adapters.openai_adapter import OpenAIAdapter
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAIAdapter(**kwargs)
    if provider == "openai_compatible":
        from ai_providers.adapters.openai_adapter import OpenAICompatibleAdapter
        if not base_url:
            raise ValueError("openai_compatible qualification requires --base-url")
        return OpenAICompatibleAdapter(api_key=api_key, base_url=base_url)
    if provider == "anthropic":
        from ai_providers.adapters.anthropic_adapter import AnthropicAdapter
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return AnthropicAdapter(**kwargs)
    if provider == "google":
        from ai_providers.adapters.google_adapter import GoogleAdapter
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return GoogleAdapter(**kwargs)
    if provider == "ollama":
        from ai_providers.adapters.ollama_adapter import OllamaAdapter
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        return OllamaAdapter(**kwargs)
    raise ValueError(f"unsupported canary provider: {provider}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Qualify one real provider/backend through RESIDUAL's adapter contract")
    parser.add_argument("--provider", choices=["openai", "openai_compatible", "anthropic", "google", "ollama"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-env", default="RESIDUAL_QUALIFICATION_LLM_API_KEY")
    parser.add_argument("--require-usage", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    key = os.environ.get(args.api_key_env)
    if args.provider != "ollama" and not key:
        report = {
            "schema": "residual.qualification.provider-canary.v1",
            "result": "UNKNOWN",
            "provider": args.provider,
            "model": args.model,
            "reason": f"credential environment {args.api_key_env} is absent",
            "non_claim": "No live-provider result was inferred from fixture or transport-only evidence.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2

    started = time.perf_counter()
    try:
        client = adapter(args.provider, key, args.base_url)
        request = ChatRequest(
            model=args.model,
            messages=(Message(Role.USER, f"Reply with exactly {CANARY} and nothing else."),),
            temperature=0,
            max_tokens=32,
            seed=20260916,
        )
        response = client.chat(request)
        latency_ms = (time.perf_counter() - started) * 1000.0
        normalized = response.content.strip()
        reasons = []
        if CANARY not in normalized:
            reasons.append("canary token not observed in response")
        if response.finish_reason in {"error", "unknown"}:
            reasons.append(f"unexpected finish_reason={response.finish_reason}")
        total_tokens = response.usage.get("total_tokens")
        if args.require_usage and (type(total_tokens) is not int or total_tokens <= 0):
            reasons.append("provider did not return positive total_tokens usage")
        report = {
            "schema": "residual.qualification.provider-canary.v1",
            "result": "PASS" if not reasons else "FAIL",
            "provider": args.provider,
            "model_requested": args.model,
            "model_returned": response.model,
            "finish_reason": response.finish_reason,
            "latency_ms": latency_ms,
            "usage": response.usage,
            "response_length": len(response.content),
            "response_sha256": hashlib.sha256(response.content.encode("utf-8")).hexdigest(),
            "canary_observed": CANARY in normalized,
            "reasons": reasons,
            "non_claim": "This proves one bounded live adapter execution and evidence completeness; it does not establish model quality or production reliability.",
        }
    except Exception as exc:
        report = {
            "schema": "residual.qualification.provider-canary.v1",
            "result": "FAIL",
            "provider": args.provider,
            "model_requested": args.model,
            "error_type": type(exc).__name__,
            "reason": str(exc)[:500],
            "non_claim": "A provider failure is retained rather than replaced by a scripted fallback.",
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["result"] == "PASS":
        return 0
    if report["result"] == "UNKNOWN":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
