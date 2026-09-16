#!/usr/bin/env python3
"""Real WebVM acceptance. Cloud failure tests never authenticate or spend money."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright
from pages_contract import validate_entry_html
from mission_smoke import workbench_acceptance
from provider_failure_smoke import provider_failure_acceptance

BOOT = "RESIDUAL BOOT: guest process attached"
PROMPT = "residual@demo:~/residual-agent-harness$"


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
    parser.add_argument("--expected-sha", required=True)
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
        report["browser_version"] = browser.version
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
            await page.wait_for_function("text => document.body.innerText.replace(/\\s/g,'').includes(text.replace(/\\s/g,''))", arg=text, timeout=timeout)

        async def wait_guest() -> None:
            await wait_text(BOOT, timeout=args.boot_timeout * 1000)
            await wait_text(PROMPT, timeout=args.boot_timeout * 1000)

        async def command_proof(command: str) -> None:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_E2E_{nonce}:"
            wire = command + "; proof_rc=$?; printf '\\nRESIDUAL_E2E_%s%s:%s\\n' '" + nonce[:8] + "' '" + nonce[8:] + "' \"$proof_rc\""
            await page.locator(".xterm-helper-textarea").focus()
            await page.keyboard.press("Control+u")
            await page.keyboard.type(wire, delay=1)
            await page.keyboard.press("Enter")
            await page.wait_for_function("prefix => new RegExp(prefix+'[0-9]+').test(document.body.innerText.replace(/\\s/g,''))", arg=prefix, timeout=180000)
            body = re.sub(r"\s", "", await page.locator("body").inner_text())
            match = re.search(re.escape(prefix) + r"(\d+)", body)
            assert match is not None, "guest exit marker disappeared"
            code = int(match[1])
            report.setdefault("guest_proofs", []).append({"command": command, "observed_exit_marker": match[0], "exit_status": code})
            assert code == 0, f"Guest command failed with exit {code}: {command}"

        try:
            response = await context.request.get(args.url, timeout=30000)
            assert response.ok, f"entry HTTP {response.status}"
            entry = await response.body()
            (args.output / "served-index.html").write_bytes(entry)
            validate_entry_html(entry.decode("utf-8"))
            info = await context.request.get(args.url.rstrip("/") + "/build-info.json", timeout=30000)
            assert info.ok, f"build identity HTTP {info.status}"
            identity = await info.json()
            report["build_identity"] = identity
            assert identity.get("commit") == args.expected_sha, "served commit differs from expected commit"
            assert hashlib.sha256(entry).hexdigest() == identity["files"]["index.html"], "served entry hash mismatch"
            worker = await context.request.get(args.url.rstrip("/") + "/serviceWorker.js", timeout=30000)
            assert worker.ok, f"service worker HTTP {worker.status}"
            assert hashlib.sha256(await worker.body()).hexdigest() == identity["files"]["serviceWorker.js"], "served service-worker hash mismatch"
            await stage("served_artifact_identity_verified")
            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await stage("document_loaded")
            await wait_guest()
            await stage("guest_attached_and_shell_ready")
            await page.locator("#mc-terminal").click()
            assert await page.evaluate("window.crossOriginIsolated"), "guest page is not cross-origin isolated"
            assert await page.evaluate("window.top === window"), "WebVM is not top-level"
            assert not report["optional_requests"], "optional service initialized before cloud opt-in"
            await command_proof("test \"$RESIDUAL_WEBVM_SLEEP_BACKEND\" = legacy-nanosleep && python3 -c 'from residual.workbench.webvm_wait import sleep; [sleep(0.05) for _ in range(300)]'")
            await stage("webvm_sleep_backend_crosses_time64_boundary")
            await command_proof('test "$PWD" = /opt/residual && test -f pyproject.toml && python3 -c "import residual" && demo > /tmp/demo-cli.json && cat /tmp/demo-cli.json && verify-demo && python3 demo/vm/guest_result_check.py runs/demo/result.json /tmp/demo-cli.json')
            await stage("real_demo_verify_and_finite_metrics_passed")
            await page.screenshot(path=str(args.output / "demo-passed.png"))
            await page.reload(wait_until="domcontentloaded")
            await wait_guest()
            await command_proof("test -s runs/demo/trace.jsonl && verify-demo")
            await stage("warm_reload_and_verify_passed")
            assert not report["optional_requests"], "cloud SDK loaded without opt-in"
            await workbench_acceptance(page, context, args, report, command_proof, stage)
            await provider_failure_acceptance(page, context, args, report, stage)
            assert not report["errors"], "unhandled browser JavaScript error"
            report["status"] = "PASS"
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
        finally:
            try:
                report["page_state"] = await page.evaluate("({url:location.pathname, isolated:window.crossOriginIsolated, controlled:!!navigator.serviceWorker.controller, title:document.title, body:document.body.innerText.slice(-20000)})")
            except Exception as error:
                report["capture_error"] = str(error)
            try:
                await page.screenshot(path=str(args.output / "final.png"), timeout=5000)
            except Exception as error:
                report["screenshot_error"] = str(error)
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
