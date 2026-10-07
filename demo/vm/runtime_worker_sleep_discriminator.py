#!/usr/bin/env python3
"""Discriminate persistent-worker PyTime failure from broader guest runtime failure.

This diagnostic targets the already-published accepted main artifact. It runs one
real audit mission through Mission Control, watches only the persistent worker's
PID/liveness for a bounded interval, and if that worker dies, launches one fresh
CPython process in the same guest that executes ``time.sleep(0.05)``.

A worker failure with a healthy fresh-process sleep materially supports a
worker-process-local/path-specific failure. It does not prove a root cause or
establish that historical corruption events share the same cause.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

BOOT = "RESIDUAL BOOT: guest process attached"
PROMPT = "residual@demo:~/residual-agent-harness$"


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--boot-timeout", type=int, default=120)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "residual.webvm-worker-sleep-discriminator.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "status": "HARNESS_FAILURE",
        "cloud_inference": "NOT_RUN",
        "commands": [],
        "errors": [],
        "console": [],
        "claim_boundary": (
            "Diagnostic evidence only. A healthy fresh-process sleep after a worker "
            "fault supports process-local/path-specific failure but does not prove root cause."
        ),
    }
    started = time.monotonic()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        report["browser_version"] = browser.version
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)[:2000]))
        page.on(
            "console",
            lambda msg: report["console"].append({"type": msg.type, "text": msg.text[:1500]})
            if len(report["console"]) < 100
            else None,
        )

        async def wait_text(text: str, timeout: int = 120000) -> None:
            await page.wait_for_function(
                "text => document.body.innerText.replace(/\\s/g,'').includes(text.replace(/\\s/g,''))",
                arg=text,
                timeout=timeout,
            )

        async def terminal_tail() -> str:
            try:
                text = await page.locator(".xterm-rows").inner_text(timeout=5000)
            except Exception:
                text = await page.locator("body").inner_text(timeout=5000)
            return text[-16000:]

        async def run_guest(command: str, *, kind: str, expect_zero: bool = True) -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_DISCRIM_{nonce}:"
            wire = (
                command
                + "; discrim_rc=$?; printf '\\nRESIDUAL_DISCRIM_%s%s:%s\\n' '"
                + nonce[:8]
                + "' '"
                + nonce[8:]
                + "' \"$discrim_rc\""
            )
            await page.locator("#mc-terminal").click()
            await page.locator(".xterm-helper-textarea").focus()
            await page.keyboard.press("Control+u")
            await page.keyboard.type(wire, delay=1)
            await page.keyboard.press("Enter")
            await page.wait_for_function(
                "prefix => new RegExp(prefix+'[0-9]+').test(document.body.innerText.replace(/\\s/g,''))",
                arg=prefix,
                timeout=180000,
            )
            body = re.sub(r"\s", "", await page.locator("body").inner_text())
            match = re.search(re.escape(prefix) + r"(\d+)", body)
            if match is None:
                raise AssertionError("guest discriminator exit marker disappeared")
            code = int(match[1])
            report["commands"].append(
                {
                    "kind": kind,
                    "command": command,
                    "exit_status": code,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "terminal_tail": await terminal_tail(),
                }
            )
            if expect_zero and code != 0:
                raise AssertionError(f"Guest command failed with exit {code}: {command}")
            return code

        try:
            info = await context.request.get(args.url.rstrip("/") + "/build-info.json", timeout=30000)
            assert info.ok, f"build identity HTTP {info.status}"
            identity = await info.json()
            report["build_identity"] = identity
            assert identity.get("commit") == args.expected_sha, "served commit differs from expected commit"

            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await wait_text(BOOT, timeout=args.boot_timeout * 1000)
            await wait_text(PROMPT, timeout=args.boot_timeout * 1000)
            assert await page.evaluate("window.crossOriginIsolated"), "guest page is not cross-origin isolated"

            baseline_sleep = await run_guest(
                "python3 -c \"import time; print('FRESH_SLEEP_BASELINE_START', time.monotonic()); "
                "time.sleep(0.05); print('FRESH_SLEEP_BASELINE_PASS', time.monotonic())\"",
                kind="fresh-sleep-baseline",
            )
            assert baseline_sleep == 0

            await page.locator("#mc-mission").click()
            await page.get_by_text("Run controls", exact=True).click()
            await page.locator("#mc-mode").select_option("audit")
            await page.locator("#mc-prompt").fill(
                "Discriminate persistent worker time behavior " + secrets.token_hex(4)
            )
            await page.locator("#mc-files").fill("residual/cli.py\nresidual/engine.py")
            await page.locator("#mc-run").click()
            await page.wait_for_function(
                "() => document.querySelector('#mc-verdict').textContent.startsWith('PASSED') "
                "&& !document.querySelector('#mc-result').hidden",
                timeout=120000,
            )
            report["audit_mission"] = "PASS"

            # The prior exact-main failure occurred shortly after the first mission.
            # Use only Bash and /bin/sleep while observing the worker so this watch
            # does not introduce another CPython process before classification.
            worker_watch = await run_guest(
                "for i in {1..40}; do "
                "if [ ! -r /tmp/residual-workbench.pid ]; then echo DISCRIM_WORKER=PID_MISSING; exit 41; fi; "
                "read -r p < /tmp/residual-workbench.pid; "
                "if ! kill -0 \"$p\" 2>/dev/null; then echo DISCRIM_WORKER=DEAD; exit 42; fi; "
                "/bin/sleep 0.25; done; echo DISCRIM_WORKER=ALIVE",
                kind="worker-watch",
                expect_zero=False,
            )
            report["worker_watch_exit_status"] = worker_watch

            if worker_watch in (41, 42):
                fresh_sleep = await run_guest(
                    "python3 -c \"import time; print('FRESH_SLEEP_AFTER_WORKER_FAULT_START', time.monotonic()); "
                    "time.sleep(0.05); print('FRESH_SLEEP_AFTER_WORKER_FAULT_PASS', time.monotonic())\"",
                    kind="fresh-sleep-after-worker-fault",
                    expect_zero=False,
                )
                report["fresh_sleep_after_worker_fault_exit_status"] = fresh_sleep
                tail = await terminal_tail()
                report["worker_trace_contains_pytime_overflow"] = (
                    "OverflowError: timestamp too large to convert to C _PyTime_t" in tail
                )
                if fresh_sleep == 0:
                    report["classification"] = "WORKER_PROCESS_LOCAL_OR_PATH_SPECIFIC_SUPPORTED"
                else:
                    report["classification"] = "BROADER_GUEST_TIME_RUNTIME_FAILURE_SUPPORTED"
                report["status"] = "WORKER_FAULT_OBSERVED"
            elif worker_watch == 0:
                report["classification"] = "NO_WORKER_FAILURE_REPRODUCED_IN_BOUNDED_WINDOW"
                report["status"] = "NO_REPRODUCTION"
            else:
                report["classification"] = "HARNESS_OR_UNCLASSIFIED_WORKER_WATCH_FAILURE"
                report["status"] = "HARNESS_FAILURE"
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
        finally:
            try:
                report["terminal_tail"] = await terminal_tail()
            except Exception as error:
                report["terminal_capture_error"] = str(error)
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
            print("WEBVM_WORKER_SLEEP_DISCRIMINATOR: " + json.dumps(report), flush=True)

    # Preserve visible failure if the worker fault recurs. No-reproduction is a
    # completed bounded diagnostic, not a reliability PASS.
    if report["status"] == "WORKER_FAULT_OBSERVED":
        return 1
    return 0 if report["status"] == "NO_REPRODUCTION" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
