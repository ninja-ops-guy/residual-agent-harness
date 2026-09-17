#!/usr/bin/env python3
"""Measure the WebVM guest CPython sleep failure threshold for one sleep duration."""
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
STATUS = "/tmp/residual-sleep-threshold.status"
LOG = "/tmp/residual-sleep-threshold.log"

PROBE_CODE = r'''
import os, pathlib, time
sleep_s = float(os.environ["RESIDUAL_SLEEP_SECONDS"])
limit = int(os.environ["RESIDUAL_SLEEP_LIMIT"])
status = pathlib.Path("/tmp/residual-sleep-threshold.status")
log_path = pathlib.Path("/tmp/residual-sleep-threshold.log")
start_wall = time.time_ns()
start_mono = time.monotonic_ns()
start_perf = time.perf_counter_ns()
count = 0
with log_path.open("w", encoding="utf-8", buffering=1) as log:
    log.write(f"START pid={os.getpid()} sleep_s={sleep_s!r} limit={limit} wall_ns={start_wall} mono_ns={start_mono} perf_ns={start_perf}\n")
    try:
        for count in range(1, limit + 1):
            pre_wall = time.time_ns()
            pre_mono = time.monotonic_ns()
            pre_perf = time.perf_counter_ns()
            if count % 25 == 0 or count >= max(1, limit - 20):
                log.write(f"PRE count={count} wall_ns={pre_wall} mono_ns={pre_mono} perf_ns={pre_perf} mono_delta_ns={pre_mono-start_mono}\n")
            try:
                time.sleep(sleep_s)
            except BaseException as exc:
                post_wall = time.time_ns()
                post_mono = time.monotonic_ns()
                post_perf = time.perf_counter_ns()
                msg = str(exc).replace("\n", " ")[:500]
                line = (
                    f"FAIL count={count} type={type(exc).__name__} message={msg} "
                    f"wall_ns={post_wall} mono_ns={post_mono} perf_ns={post_perf} "
                    f"mono_delta_ns={post_mono-start_mono}\n"
                )
                log.write(line); status.write_text(line, encoding="utf-8"); raise
        end_mono = time.monotonic_ns()
        line = f"PASS count={count} mono_delta_ns={end_mono-start_mono}\n"
        log.write(line); status.write_text(line, encoding="utf-8")
    except BaseException:
        raise
'''


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--expected-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sleep-seconds", type=float, required=True)
    p.add_argument("--iterations", type=int, required=True)
    p.add_argument("--boot-timeout", type=int, default=120)
    args = p.parse_args()
    if not 0 <= args.sleep_seconds <= 1:
        p.error("--sleep-seconds must be 0..1")
    if not 50 <= args.iterations <= 2500:
        p.error("--iterations must be 50..2500")
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "residual.webvm-runtime-sleep-threshold.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "sleep_seconds": args.sleep_seconds,
        "iterations_requested": args.iterations,
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

        async def tail() -> str:
            try:
                value = await page.locator(".xterm-rows").inner_text(timeout=5000)
            except Exception:
                value = await page.locator("body").inner_text(timeout=5000)
            return value[-14000:]

        async def guest(command: str, *, kind: str, expect_zero: bool = True, timeout: int = 240000) -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_SLEEPTH_{nonce}:"
            wire = (
                command
                + "; rc=$?; printf '\\nRESIDUAL_SLEEPTH_%s%s:%s\\n' '"
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
            rc = int(match[1])
            report["commands"].append({
                "kind": kind,
                "exit_status": rc,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "terminal_tail": await tail(),
            })
            if expect_zero and rc:
                raise AssertionError(f"guest command failed with exit {rc}: {command}")
            return rc

        async def status_code() -> int:
            return await guest(
                f"if grep -q '^PASS ' {STATUS} 2>/dev/null; then (exit 41); "
                f"elif grep -q '^FAIL ' {STATUS} 2>/dev/null; then (exit 42); "
                f"else (exit 43); fi",
                kind="status",
                expect_zero=False,
            )

        try:
            entry_response = await context.request.get(args.url, timeout=30000)
            assert entry_response.ok
            entry = await entry_response.body()
            validate_entry_html(entry.decode("utf-8"))
            info_response = await context.request.get(args.url.rstrip("/") + "/build-info.json", timeout=30000)
            assert info_response.ok
            identity = await info_response.json()
            report["build_identity"] = identity
            assert identity.get("commit") == args.expected_sha
            assert hashlib.sha256(entry).hexdigest() == identity["files"]["index.html"]

            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await wait_text(BOOT, args.boot_timeout * 1000)
            await wait_text(PROMPT, args.boot_timeout * 1000)
            assert await page.evaluate("window.crossOriginIsolated")
            assert await page.evaluate("window.top === window")
            await guest(f"test ! -e {WORKER_PID}; rm -f {STATUS} {LOG}", kind="precondition")

            rc = await guest(
                "RESIDUAL_SLEEP_SECONDS=" + shlex.quote(repr(args.sleep_seconds))
                + " RESIDUAL_SLEEP_LIMIT=" + shlex.quote(str(args.iterations))
                + " python3 -u -c " + shlex.quote(PROBE_CODE)
                + " >/tmp/residual-sleep-threshold.stdout 2>&1",
                kind="threshold-probe",
                expect_zero=False,
                timeout=max(240000, int(args.iterations * max(args.sleep_seconds, 0.01) * 3000 + 120000)),
            )
            state = await status_code()
            report["probe_process_exit"] = rc
            report["status_exit"] = state
            await guest(
                f"printf 'THRESHOLD_STATUS '; cat {STATUS} 2>/dev/null || echo MISSING; "
                f"printf 'THRESHOLD_LOG_BEGIN\\n'; cat {LOG} 2>/dev/null || true; printf 'THRESHOLD_LOG_END\\n'; "
                f"test ! -e {WORKER_PID}",
                kind="evidence",
            )
            if state == 42 and rc != 0:
                report["classification"] = "SLEEP_THRESHOLD_FAILURE"
            elif state == 41 and rc == 0:
                report["classification"] = "BOUNDED_PASS"
                report["status"] = "PASS"
            else:
                report["classification"] = "RESULT_INCONSISTENT"
        except Exception as exc:
            report["failure"] = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                report["page_state"] = await page.evaluate(
                    "({url:location.pathname,isolated:window.crossOriginIsolated,controlled:!!navigator.serviceWorker.controller,body:document.body.innerText.slice(-18000)})"
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
            print("WEBVM_SLEEP_THRESHOLD_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
