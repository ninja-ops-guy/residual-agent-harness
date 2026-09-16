#!/usr/bin/env python3
"""Run an independent sleep canary beside the first Mission Control worker."""
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
CANARY_PID = "/tmp/residual-sleep-canary.pid"
CANARY_STATUS = "/tmp/residual-sleep-canary.status"
CANARY_LOG = "/tmp/residual-sleep-canary.log"
CANARY_CODE = r'''
import os, pathlib, time
status = pathlib.Path("/tmp/residual-sleep-canary.status")
log_path = pathlib.Path("/tmp/residual-sleep-canary.log")
count = 0
with log_path.open("w", encoding="utf-8", buffering=1) as log:
    log.write(f"START pid={os.getpid()}\n")
    try:
        for count in range(1, 2401):
            time.sleep(0.05)
            if count % 100 == 0:
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
    p.add_argument("--observation-seconds", type=int, default=130)
    p.add_argument("--boot-timeout", type=int, default=120)
    args = p.parse_args()
    if not 30 <= args.observation_seconds <= 240:
        p.error("--observation-seconds must be 30..240")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "residual.webvm-runtime-sleep-canary.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "intervention": "second_long_lived_guest_cpython_repeating_time_sleep_0_05",
        "claim_boundary": "diagnostic concurrency intervention; not production reliability evidence",
        "cloud_inference": "NOT_RUN",
        "status": "FAIL",
        "classification": "UNCLASSIFIED",
        "commands": [],
        "polls": [],
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
            return value[-12000:]

        async def guest(command: str, *, kind: str, expect_zero: bool = True) -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_CANARY_{nonce}:"
            wire = (
                command
                + "; rc=$?; printf '\\nRESIDUAL_CANARY_%s%s:%s\\n' '"
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
                timeout=180000,
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
                "terminal_tail": await tail(),
            })
            if expect_zero and code:
                raise AssertionError(f"guest command failed with {code}: {command}")
            return code

        health = (
            "w=0; c=0; d=0; "
            f"if [ -f {WORKER_PID} ] && read -r p < {WORKER_PID} && [[ \"$p\" =~ ^[0-9]+$ ]] && kill -0 \"$p\" 2>/dev/null; then w=1; fi; "
            f"if [ -f {CANARY_PID} ] && read -r q < {CANARY_PID} && [[ \"$q\" =~ ^[0-9]+$ ]] && kill -0 \"$q\" 2>/dev/null; then c=1; fi; "
            f"[ -f {CANARY_STATUS} ] && d=1 || true; "
            "printf 'HEALTH worker=%s canary=%s done=%s\\n' \"$w\" \"$c\" \"$d\"; "
            "if [ \"$w$c\" = 11 ]; then true; "
            "elif [ \"$w$c\" = 01 ]; then (exit 21); "
            "elif [ \"$w$c$d\" = 101 ]; then (exit 22); "
            "elif [ \"$w$c\" = 00 ]; then (exit 23); else (exit 24); fi"
        )

        async def state() -> str:
            code = await guest(
                f"if grep -q '^PASS ' {CANARY_STATUS} 2>/dev/null; then (exit 41); "
                f"elif grep -q '^FAIL ' {CANARY_STATUS} 2>/dev/null; then (exit 42); "
                f"else (exit 43); fi",
                kind="canary-state",
                expect_zero=False,
            )
            return {41: "PASS", 42: "FAIL", 43: "MISSING"}.get(
                code, f"UNEXPECTED_EXIT_{code}"
            )

        try:
            entry_response = await context.request.get(args.url, timeout=30000)
            assert entry_response.ok, f"entry HTTP {entry_response.status}"
            entry = await entry_response.body()
            validate_entry_html(entry.decode())
            info_response = await context.request.get(
                args.url.rstrip("/") + "/build-info.json", timeout=30000
            )
            assert info_response.ok, f"build-info HTTP {info_response.status}"
            identity = await info_response.json()
            report["build_identity"] = identity
            assert identity.get("commit") == args.expected_sha
            assert hashlib.sha256(entry).hexdigest() == identity["files"]["index.html"]

            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await wait_text(BOOT, args.boot_timeout * 1000)
            await wait_text(PROMPT, args.boot_timeout * 1000)
            assert await page.evaluate("window.crossOriginIsolated")
            assert await page.evaluate("window.top === window")

            launch = (
                f"rm -f {CANARY_PID} {CANARY_STATUS} {CANARY_LOG}; "
                "python3 -u -c " + shlex.quote(CANARY_CODE)
                + " >/tmp/residual-sleep-canary.stdout 2>&1 & q=$!; "
                f"printf '%s\\n' \"$q\" > {CANARY_PID}; kill -0 \"$q\""
            )
            await guest(launch, kind="canary-launch")
            pre = await guest(health, kind="health-before-mission", expect_zero=False)
            assert pre == 21, f"expected worker absent/canary alive before mission, got {pre}"

            await page.locator("#mc-mission").click()
            await page.get_by_text("Run controls", exact=True).click()
            await page.locator("#mc-mode").select_option("audit")
            await page.locator("#mc-prompt").fill(
                "Inspect these actual repository sources " + secrets.token_hex(4)
            )
            await page.locator("#mc-files").fill("residual/cli.py\nresidual/engine.py")
            await page.locator("#mc-run").click()
            await page.wait_for_function(
                "() => document.querySelector('#mc-verdict').textContent.startsWith('PASSED') && !document.querySelector('#mc-result').hidden",
                timeout=120000,
            )
            report["first_audit_mission"] = "PASS"

            terminal_class = None
            deadline = time.monotonic() + args.observation_seconds
            while time.monotonic() < deadline:
                code = await guest(health, kind="health-poll", expect_zero=False)
                report["polls"].append({
                    "exit_status": code,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                })
                if code != 0:
                    terminal_class = {
                        21: "WORKER_FAILED_CANARY_HEALTHY",
                        22: "CANARY_EXITED_WORKER_HEALTHY",
                        23: "WORKER_AND_CANARY_NOT_ALIVE",
                        24: "HEALTH_STATE_INCOMPLETE",
                    }.get(code, f"UNEXPECTED_HEALTH_CODE_{code}")
                    break
                await asyncio.sleep(5)

            canary_state = await state()
            report["canary_state"] = canary_state
            await guest(
                f"printf 'CANARY_STATUS '; cat {CANARY_STATUS} 2>/dev/null || echo MISSING; "
                f"printf 'CANARY_LOG_BEGIN\\n'; cat {CANARY_LOG} 2>/dev/null || true; printf 'CANARY_LOG_END\\n'",
                kind="canary-evidence",
            )
            worker_final = await guest(
                f"if [ -f {WORKER_PID} ] && read -r p < {WORKER_PID} && kill -0 \"$p\" 2>/dev/null; then true; else (exit 31); fi",
                kind="worker-final",
                expect_zero=False,
            )
            worker_alive = worker_final == 0
            report["worker_final_alive"] = worker_alive

            if terminal_class == "WORKER_FAILED_CANARY_HEALTHY":
                report["classification"] = terminal_class
            elif canary_state == "FAIL":
                report["classification"] = (
                    "CANARY_FAILED_WORKER_HEALTHY" if worker_alive else "WORKER_AND_CANARY_FAILED"
                )
            elif canary_state == "PASS" and worker_alive:
                report["classification"] = "NO_FAILURE_OBSERVED_BOUNDED_CANARY_PASS"
                report["status"] = "PASS"
            elif canary_state == "PASS" and not worker_alive:
                report["classification"] = "WORKER_FAILED_CANARY_COMPLETED_PASS"
            else:
                report["classification"] = terminal_class or "OBSERVATION_INCONCLUSIVE"

        except Exception as exc:
            report["failure"] = f"{type(exc).__name__}: {exc}"
            try:
                report["canary_state_on_exception"] = await state()
            except Exception as state_exc:
                report["canary_state_error"] = f"{type(state_exc).__name__}: {state_exc}"
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
            print("WEBVM_SLEEP_CANARY_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
