#!/usr/bin/env python3
"""Production provider-helper acceptance without authentication or inference.

This test deliberately loads the REAL Puter browser SDK from js.puter.com on the
published Pages origin. It proves the service-worker/header boundary permits the
SDK to initialize. It MUST NOT sign in, list models, or invoke inference.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from playwright.async_api import async_playwright


def safe_url(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}{p.path}"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-url", required=True, help="Published Pages root URL")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mobile", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "FAIL",
        "provider_url": safe_url(urljoin(args.page_url.rstrip('/') + '/', 'provider/')),
        "viewport": "narrow" if args.mobile else "desktop",
        "real_puter_sdk": "NOT_RUN",
        "authentication": "NOT_RUN",
        "inference": "NOT_RUN",
        "errors": [],
        "failed_requests": [],
        "console": [],
    }
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(viewport={"width": 390, "height": 844} if args.mobile else {"width": 1280, "height": 800})
        page = await context.new_page()
        page.on("pageerror", lambda e: report["errors"].append(str(e)[:2000]))
        page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:1500]}) if len(report["console"]) < 100 else None)
        context.on("requestfailed", lambda r: report["failed_requests"].append({"url": safe_url(r.url), "error": r.failure}) if len(report["failed_requests"]) < 100 else None)
        try:
            provider_url = report["provider_url"]
            response = await page.goto(provider_url, wait_until="domcontentloaded", timeout=60000)
            assert response and response.ok, f"provider helper HTTP {response.status if response else 'none'}"
            assert not await page.evaluate("window.crossOriginIsolated"), "provider helper inherited COOP/COEP isolation"
            assert await page.locator("#load").is_enabled(), "Load Puter is unavailable"
            await page.locator("#load").click()
            await page.wait_for_function("() => !!window.puter?.auth && !!window.puter?.ai", timeout=20000)
            status = await page.locator("#status").inner_text()
            assert "SDK loaded" in status or "Connected" in status, status
            puter_failures = [item for item in report["failed_requests"] if urlsplit(item["url"]).hostname == "js.puter.com"]
            assert not puter_failures, f"real Puter SDK request failed: {puter_failures}"
            assert not any("cross-origin-resource-policy" in item["text"].lower() or "err_failed" in item["text"].lower() for item in report["console"]), "browser reported cross-origin SDK failure"
            report["real_puter_sdk"] = "PASS_LOADED_FROM_JS_PUTER_COM"
            report["status"] = "PASS"
            await page.screenshot(path=str(args.output / "provider-sdk-loaded.png"))
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
        finally:
            await browser.close()
            (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("PROVIDER_SDK_REPORT: " + json.dumps(report), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
