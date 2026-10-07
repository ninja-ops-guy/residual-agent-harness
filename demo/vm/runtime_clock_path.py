#!/usr/bin/env python3
"""Discriminate WebVM CPython sleep-path failures from direct monotonic-clock reads."""
from __future__ import annotations

import argparse
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
STATUS = "/tmp/residual-clock-path.status"
LOG = "/tmp/residual-clock-path.log"

PROBE_CODE = r'''
import os, pathlib, time
mode = os.environ["RESIDUAL_CLOCK_MODE"]
limit = int(os.environ["RESIDUAL_CLOCK_LIMIT"])
status = pathlib.Path("/tmp/residual-clock-path.status")
log_path = pathlib.Path("/tmp/residual-clock-path.log")
clock_id = getattr(time, "CLOCK_MONOTONIC", None)
count = 0

def snapshot(label):
    parts = [label]
    try:
        parts.append("clock_float=" + repr(time.clock_gettime(clock_id)))
    except BaseException as exc:
        parts.append("clock_float_error=" + type(exc).__name__ + ":" + str(exc).replace("\n", " ")[:200])
    try:
        parts.append("clock_ns=" + str(time.clock_gettime_ns(clock_id)))
    except BaseException as exc:
        parts.append("clock_ns_error=" + type(exc).__name__ + ":" + str(exc).replace("\n", " ")[:200])
    try:
        parts.append("monotonic_ns=" + str(time.monotonic_ns()))
    except BaseException as exc:
        parts.append("monotonic_ns_error=" + type(exc).__name__ + ":" + str(exc).replace("\n", " ")[:200])
    return " ".join(parts)

with log_path.open("w", encoding="utf-8", buffering=1) as log:
    log.write(f"START pid={os.getpid()} mode={mode} limit={limit} {snapshot('initial')}\n")
    try:
        for count in range(1, limit + 1):
            if mode == "sleep-zero":
                time.sleep(0.0)
                value = None
            elif mode == "sleep-100ms":
                time.sleep(0.1)
                value = None
            elif mode == "monotonic-ns":
                value = time.monotonic_ns()
            elif mode == "clock-gettime-ns":
                value = time.clock_gettime_ns(clock_id)
            elif mode == "clock-gettime-float":
                value = time.clock_gettime(clock_id)
            else:
                raise RuntimeError("unknown mode: " + mode)
            if count % 100 == 0 or count in (1, 250, 270, 271, 272, 273, 274, 275):
                log.write(f"STEP count={count} value={value!r}\n")
    except BaseException as exc:
        msg = str(exc).replace("\n", " ")[:500]
        line = f"FAIL count={count} type={type(exc).__name__} message={msg} {snapshot('after_failure')}\n"
        log.write(line)
        status.write_text(line, encoding="utf-8")
        raise
    else:
        line = f"PASS count={count} {snapshot('final')}\n"
        log.write(line)
        status.write_text(line, encoding="utf-8")
'''


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--expected-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--mode",
        choices=(
            "sleep-zero",
            "sleep-100ms",
            "monotonic-ns",
            "clock-gettime-ns",
            "clock-gettime-float",
        ),
        required=True,
    )
    p.add_argument("--iterations", type=int, required=True)
    p.add_argument("--boot-timeout", type=int, default=120)
    args = p.parse_args()
    if not 100 <= args.iterations <= 5000:
        p.error("--iterations must be 100..5000")
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "residual.webvm-runtime-clock-path.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "mode": args.mode,
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

        async def terminal_tail() -> str:
            try:
                value = await page.locator(".xterm-rows").inner_text(timeout=5000)
            except Exception:
                value = await page.locator("body").inner_text(timeout=5000)
            return value[-16000:]

        async def guest(command: str, *, kind: str, expect_zero: bool = True, timeout: int = 300000) -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_CLOCKPATH_{nonce}:"
            wire = (
                command
                + "; rc=$?; printf '\\nRESIDUAL_CLOCKPATH_%s%s:%s\\n' '"
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
                "terminal_tail": await terminal_tail(),
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
            await guest(f"test ! -e {WORKER_PID}; rm -f {STATUS} {LOG}", kind="precondition")

            rc = await guest(
                "RESIDUAL_CLOCK_MODE=" + shlex.quote(args.mode)
                + " RESIDUAL_CLOCK_LIMIT=" + shlex.quote(str(args.iterations))
                + " python3 -u -c " + shlex.quote(PROBE_CODE)
                + " >/tmp/residual-clock-path.stdout 2>&1",
                kind="clock-path-probe",
                expect_zero=False,
                timeout=max(300000, int((35 if args.mode == "sleep-100ms" else 5) * 1000 + 180000)),
            )
            state = await status_code()
            report["probe_process_exit"] = rc
            report["status_exit"] = state
            await guest(
                f"printf 'CLOCK_PATH_STATUS '; cat {STATUS} 2>/dev/null || echo MISSING; "
                f"printf 'CLOCK_PATH_LOG_BEGIN\\n'; cat {LOG} 2>/dev/null || true; printf 'CLOCK_PATH_LOG_END\\n'; "
                f"test ! -e {WORKER_PID}",
                kind="evidence",
            )
            if state == 42 and rc != 0:
                report["classification"] = "CLOCK_PATH_FAILURE"
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
                    "({url:location.pathname,isolated:window.crossOriginIsolated,controlled:!!navigator.serviceWorker.controller,body:document.body.innerText.slice(-20000)})"
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
            print("WEBVM_CLOCK_PATH_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    raise SystemExit(asyncio.run(main()))
