#!/usr/bin/env python3
"""Discriminate foreground/background long-lived CPython sleep failures without Mission Control."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import secrets
import shlex
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright
from pages_contract import validate_entry_html

BOOT = "RESIDUAL BOOT: guest process attached"
PROMPT = "residual@demo:~/residual-agent-harness$"
WORKER_PID = "/tmp/residual-workbench.pid"
STATUS = "/tmp/residual-sleep-isolation.status"
LOG = "/tmp/residual-sleep-isolation.log"
PID = "/tmp/residual-sleep-isolation.pid"

CANARY_CODE = r'''
import os, pathlib, time
limit = int(os.environ.get("RESIDUAL_CANARY_LIMIT", "400"))
status = pathlib.Path("/tmp/residual-sleep-isolation.status")
log_path = pathlib.Path("/tmp/residual-sleep-isolation.log")
count = 0
with log_path.open("w", encoding="utf-8", buffering=1) as log:
    log.write(f"START pid={os.getpid()} limit={limit}\n")
    try:
        for count in range(1, limit + 1):
            time.sleep(0.05)
            if count % 50 == 0:
                log.write(f"TICK count={count}\n")
    except BaseException as exc:
        msg = str(exc).replace("\n", " ")[:500]
        line = f"FAIL count={count} type={type(exc).__name__} message={msg}\n"
        log.write(line); status.write_text(line, encoding="utf-8"); raise
    else:
        line = f"PASS count={count}\n"
        log.write(line); status.write_text(line, encoding="utf-8")
'''


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--expected-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mode", choices=("foreground", "background"), required=True)
    p.add_argument("--sleeps", type=int, default=400)
    p.add_argument("--boot-timeout", type=int, default=120)
    args = p.parse_args()
    if not 300 <= args.sleeps <= 1200:
        p.error("--sleeps must be between 300 and 1200")

    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "residual.webvm-runtime-sleep-isolation.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "mode": args.mode,
        "sleeps_requested": args.sleeps,
        "sleep_seconds": 0.05,
        "mission_control_worker": "MUST_REMAIN_ABSENT",
        "cloud_inference": "NOT_RUN",
        "status": "FAIL",
        "classification": "UNCLASSIFIED",
        "commands": [],
    }
    started = time.monotonic()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()

        async def wait_text(text: str, timeout: int = 120000) -> None:
            await page.wait_for_function(
                "t => document.body.innerText.replace(/\\s/g,'').includes(t.replace(/\\s/g,''))",
                arg=text,
                timeout=timeout,
            )

        async def terminal_tail() -> str:
            try:
                value = await page.locator(".xterm-rows").inner_text(timeout=5000)
            except Exception:
                value = await page.locator("body").inner_text(timeout=5000)
            return value[-10000:]

        async def guest(command: str, *, kind: str, expect_zero: bool = True, timeout: int = 180000) -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_SLEEPISO_{nonce}:"
            wire = (
                command
                + "; rc=$?; printf '\\nRESIDUAL_SLEEPISO_%s%s:%s\\n' '"
                + nonce[:8] + "' '" + nonce[8:] + "' \"$rc\""
            )
            await page.locator("#mc-terminal").click()
            await page.locator(".xterm-helper-textarea").focus()
            await page.keyboard.press("Control+u")
            await page.keyboard.type(wire, delay=1)
            await page.keyboard.press("Enter")
            await page.wait_for_function(
                "p => new RegExp(p+'[0-9]+').test(document.body.innerText.replace(/\\s/g,''))",
                arg=prefix,
                timeout=timeout,
            )
            body = re.sub(r"\s", "", await page.locator("body").inner_text())
            match = re.search(re.escape(prefix) + r"(\d+)", body)
            if not match:
                raise AssertionError("guest exit marker disappeared")
            code = int(match[1])
            report["commands"].append({
                "kind": kind,
                "exit_status": code,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "terminal_tail": await terminal_tail(),
            })
            if expect_zero and code:
                raise AssertionError(f"guest command failed with exit {code}: {command}")
            return code

        async def status_code() -> int:
            return await guest(
                f"if grep -q '^PASS ' {STATUS} 2>/dev/null; then (exit 41); "
                f"elif grep -q '^FAIL ' {STATUS} 2>/dev/null; then (exit 42); "
                f"else (exit 43); fi",
                kind="status",
                expect_zero=False,
            )

        async def retain_evidence() -> None:
            await guest(
                f"printf 'ISOLATION_STATUS '; cat {STATUS} 2>/dev/null || echo MISSING; "
                f"printf 'ISOLATION_LOG_BEGIN\\n'; cat {LOG} 2>/dev/null || true; printf 'ISOLATION_LOG_END\\n'; "
                f"test ! -e {WORKER_PID}",
                kind="evidence",
            )

        try:
            entry_response = await context.request.get(args.url, timeout=30000)
            assert entry_response.ok, f"entry HTTP {entry_response.status}"
            entry = await entry_response.body()
            validate_entry_html(entry.decode("utf-8"))
            info_response = await context.request.get(args.url.rstrip("/") + "/build-info.json", timeout=30000)
            assert info_response.ok, f"build-info HTTP {info_response.status}"
            identity = await info_response.json()
            report["build_identity"] = identity
            assert identity.get("commit") == args.expected_sha, "served commit differs from expected"
            assert hashlib.sha256(entry).hexdigest() == identity["files"]["index.html"], "entry hash mismatch"

            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await wait_text(BOOT, args.boot_timeout * 1000)
            await wait_text(PROMPT, args.boot_timeout * 1000)
            assert await page.evaluate("window.crossOriginIsolated")
            assert await page.evaluate("window.top === window")
            await guest(
                f"test ! -e {WORKER_PID}; rm -f {STATUS} {LOG} {PID}",
                kind="precondition",
            )

            code = shlex.quote(CANARY_CODE)
            if args.mode == "foreground":
                rc = await guest(
                    f"RESIDUAL_CANARY_LIMIT={args.sleeps} python3 -u -c {code} >/tmp/residual-sleep-isolation.stdout 2>&1",
                    kind="foreground-canary",
                    expect_zero=False,
                    timeout=max(180000, int(args.sleeps * 50 + 60000)),
                )
                state = await status_code()
                report["canary_process_exit"] = rc
                report["status_exit"] = state
                await retain_evidence()
                if state == 42 and rc != 0:
                    report["classification"] = "FOREGROUND_SLEEP_FAILED"
                elif state == 41 and rc == 0:
                    report["classification"] = "FOREGROUND_SLEEP_BOUNDED_PASS"
                    report["status"] = "PASS"
                else:
                    report["classification"] = "FOREGROUND_RESULT_INCONSISTENT"
            else:
                await guest(
                    f"RESIDUAL_CANARY_LIMIT={args.sleeps} python3 -u -c {code} >/tmp/residual-sleep-isolation.stdout 2>&1 & q=$!; "
                    f"printf '%s\\n' \"$q\" > {PID}; kill -0 \"$q\"",
                    kind="background-launch",
                )
                deadline = time.monotonic() + (args.sleeps * 0.05) + 30
                state = 43
                while time.monotonic() < deadline:
                    state = await status_code()
                    if state in (41, 42):
                        break
                    await asyncio.sleep(2)
                report["status_exit"] = state
                await retain_evidence()
                if state == 42:
                    report["classification"] = "BACKGROUND_SLEEP_FAILED_WITHOUT_MISSION_WORKER"
                elif state == 41:
                    report["classification"] = "BACKGROUND_SLEEP_BOUNDED_PASS_WITHOUT_MISSION_WORKER"
                    report["status"] = "PASS"
                else:
                    report["classification"] = "BACKGROUND_SLEEP_INCONCLUSIVE"

        except Exception as exc:
            report["failure"] = f"{type(exc).__name__}: {exc}"
            try:
                await retain_evidence()
            except Exception as evidence_exc:
                report["evidence_capture_error"] = f"{type(evidence_exc).__name__}: {evidence_exc}"
        finally:
            try:
                report["page_state"] = await page.evaluate(
                    "({url:location.pathname,isolated:window.crossOriginIsolated,controlled:!!navigator.serviceWorker.controller,body:document.body.innerText.slice(-16000)})"
                )
            except Exception as exc:
                report["page_state_error"] = str(exc)
            try:
                await page.screenshot(path=str(args.output / "final.png"), timeout=5000)
            except Exception as exc:
                report["screenshot_error"] = str(exc)
            try:
                await context.tracing.stop(path=str(args.output / "trace.zip"))
            finally:
                await browser.close()
            report["elapsed_seconds"] = round(time.monotonic() - started, 2)
            (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("WEBVM_SLEEP_ISOLATION_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
