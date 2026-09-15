#!/usr/bin/env python3
"""Exercise real WebVM, not a mocked VM or container-only approximation.

Requires Playwright and its browser binaries. Evidence is retained on failure.
No sign-in or paid inference is attempted by this test.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright


BOOT = "RESIDUAL BOOT: guest process attached"


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", choices=("chromium", "webkit"), default="chromium")
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--boot-timeout", type=int, default=120)
    parser.add_argument("--expected-sha")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"url": safe_url(args.url), "browser": args.browser,
              "viewport": "mobile" if args.mobile else "desktop",
              "expected_sha": args.expected_sha, "status": "FAIL",
              "stages": [], "errors": [], "failed_requests": [],
              "http_errors": [], "optional_requests": [], "console": [],
              "cloud_inference": "NOT_RUN"}
    started = time.monotonic()

    async with async_playwright() as pw:
        browser = await getattr(pw, args.browser).launch()
        context = await browser.new_context(viewport={"width": 390, "height": 844} if args.mobile else {"width": 1280, "height": 800})
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)[:2000]))
        page.on("console", lambda msg: report["console"].append({"type": msg.type, "text": msg.text[:1500]}) if len(report["console"]) < 100 else None)
        context.on("requestfailed", lambda req: report["failed_requests"].append({"url": safe_url(req.url), "error": req.failure}) if len(report["failed_requests"]) < 100 else None)
        context.on("response", lambda res: report["http_errors"].append({"url": safe_url(res.url), "status": res.status}) if res.status >= 400 and len(report["http_errors"]) < 100 else None)
        context.on("request", lambda req: report["optional_requests"].append(safe_url(req.url)) if urlsplit(req.url).hostname in {"plausible.leaningtech.com", "js.puter.com", "api.puter.com"} else None)

        async def stage(name: str) -> None:
            report["stages"].append({"name": name, "elapsed_seconds": round(time.monotonic() - started, 2)})
            print(f"WEBVM_STAGE: {name}", flush=True)

        async def wait_text(text: str, timeout: int = 120000) -> None:
            await page.wait_for_function("text => document.body.innerText.includes(text)", arg=text, timeout=timeout)

        async def command_proof(command: str) -> None:
            # The complete nonce is never echoed as part of the command line:
            # only an executed guest printf can produce the expected marker.
            nonce = secrets.token_hex(8)
            expected = f"RESIDUAL_E2E_{nonce}:0"
            wire = command + "; proof_rc=$?; printf '\\nRESIDUAL_E2E_%s%s:%s\\n' '" + nonce[:8] + "' '" + nonce[8:] + "' \"$proof_rc\""
            terminal = page.locator(".xterm-helper-textarea")
            await terminal.focus()
            await page.keyboard.press("Control+u")
            await page.keyboard.type(wire, delay=1)
            await page.keyboard.press("Enter")
            await wait_text(expected, timeout=180000)

        try:
            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await stage("document_loaded")
            await wait_text(BOOT, timeout=args.boot_timeout * 1000)
            await stage("guest_attached")
            assert await page.evaluate("window.crossOriginIsolated"), "guest page is not cross-origin isolated"
            assert await page.evaluate("window.top === window"), "WebVM is embedded instead of top-level"
            assert not report["optional_requests"], "optional third-party requests occurred before cloud opt-in"
            if args.expected_sha:
                response = await context.request.get(args.url.rstrip("/") + "/build-info.json")
                assert response.ok, "build identity unavailable"
                identity = await response.json()
                report["build_identity"] = identity
                assert identity.get("commit") == args.expected_sha, "deployed commit does not match expected commit"
            await command_proof('test "$PWD" = /opt/residual && test -f pyproject.toml && python3 -c "import residual" && demo && verify-demo')
            await stage("real_demo_and_verify_passed")
            await page.screenshot(path=str(args.output / "demo-passed.png"))
            await page.reload(wait_until="domcontentloaded")
            await wait_text(BOOT, timeout=args.boot_timeout * 1000)
            await command_proof("test -s runs/demo/trace.jsonl && verify-demo")
            await stage("warm_reload_and_verify_passed")
            assert not report["optional_requests"], "cloud SDK loaded without an explicit click"
            # A network-denied SDK must not take the offline guest down. This
            # avoids authenticating, creating an account, or spending money.
            await context.set_offline(True)
            await page.get_by_role("button", name="ENABLE CLOUD", exact=False).click(timeout=10000)
            await page.get_by_role("button", name="ENABLE CLOUD", exact=False).wait_for(state="visible", timeout=20000)
            await context.set_offline(False)
            await command_proof("true")
            await stage("cloud_network_failure_preserves_guest")
            assert not report["errors"], "unhandled browser JavaScript error"
            report["status"] = "PASS"
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
        finally:
            try:
                report["page_state"] = await page.evaluate("({url:location.pathname, isolated:window.crossOriginIsolated, controlled:!!navigator.serviceWorker.controller, title:document.title, body:document.body.innerText.slice(-20000)})")
                await page.screenshot(path=str(args.output / "final.png"))
            except Exception as error:
                report["capture_error"] = str(error)
            try:
                await context.tracing.stop(path=str(args.output / "trace.zip"))
            finally:
                await browser.close()
            report["elapsed_seconds"] = round(time.monotonic() - started, 2)
            (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("WEBVM_REPORT: " + json.dumps(report), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
