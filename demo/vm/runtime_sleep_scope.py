#!/usr/bin/env python3
"""Determine whether the WebVM positive-sleep boundary is per-process or guest-shared."""
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

PROBE_CODE = r'''
import os, pathlib, time
label = os.environ["RESIDUAL_SCOPE_LABEL"]
limit = int(os.environ["RESIDUAL_SCOPE_LIMIT"])
sleep_s = float(os.environ.get("RESIDUAL_SCOPE_SLEEP", "0.05"))
status = pathlib.Path(f"/tmp/residual-scope-{label}.status")
log_path = pathlib.Path(f"/tmp/residual-scope-{label}.log")
count = 0
with log_path.open("w", encoding="utf-8", buffering=1) as log:
    log.write(f"START label={label} pid={os.getpid()} limit={limit} sleep_s={sleep_s!r}\n")
    try:
        for count in range(1, limit + 1):
            time.sleep(sleep_s)
            if count % 50 == 0 or count >= max(1, limit - 5):
                log.write(f"STEP label={label} count={count}\n")
    except BaseException as exc:
        msg = str(exc).replace("\n", " ")[:500]
        parts = []
        for name, fn in (
            ("clock_float", lambda: time.clock_gettime(time.CLOCK_MONOTONIC)),
            ("clock_ns", lambda: time.clock_gettime_ns(time.CLOCK_MONOTONIC)),
            ("monotonic_ns", time.monotonic_ns),
        ):
            try:
                parts.append(f"{name}={fn()!r}")
            except BaseException as clock_exc:
                parts.append(f"{name}_error={type(clock_exc).__name__}:{clock_exc}")
        line = f"FAIL label={label} count={count} type={type(exc).__name__} message={msg} " + " ".join(parts) + "\n"
        log.write(line); status.write_text(line, encoding="utf-8"); raise
    else:
        line = f"PASS label={label} count={count}\n"
        log.write(line); status.write_text(line, encoding="utf-8")
'''

PLANS = {
    "split-200-200": (("a", 200), ("b", 200)),
    "split-272-2": (("a", 272), ("b", 2)),
    "single-273": (("a", 273),),
}


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--expected-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--plan", choices=tuple(PLANS), required=True)
    p.add_argument("--sleep-seconds", type=float, default=0.05)
    p.add_argument("--boot-timeout", type=int, default=120)
    args = p.parse_args()
    if not 0 < args.sleep_seconds <= 1:
        p.error("--sleep-seconds must be >0 and <=1")
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "residual.webvm-runtime-sleep-scope.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "plan": args.plan,
        "sleep_seconds": args.sleep_seconds,
        "mission_control_worker": "MUST_REMAIN_ABSENT",
        "cloud_inference": "NOT_RUN",
        "processes": [],
        "commands": [],
        "status": "FAIL",
        "classification": "UNCLASSIFIED",
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
            prefix = f"RESIDUAL_SCOPE_{nonce}:"
            wire = (
                command
                + "; rc=$?; printf '\\nRESIDUAL_SCOPE_%s%s:%s\\n' '"
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

        async def process_state(label: str) -> tuple[int, str]:
            status_path = f"/tmp/residual-scope-{label}.status"
            code = await guest(
                f"if grep -q '^PASS ' {status_path} 2>/dev/null; then (exit 41); "
                f"elif grep -q '^FAIL ' {status_path} 2>/dev/null; then (exit 42); "
                f"else (exit 43); fi",
                kind=f"{label}-status",
                expect_zero=False,
            )
            state = {41: "PASS", 42: "FAIL", 43: "MISSING"}.get(code, f"UNEXPECTED_{code}")
            return code, state

        async def run_process(label: str, limit: int) -> dict:
            status_path = f"/tmp/residual-scope-{label}.status"
            log_path = f"/tmp/residual-scope-{label}.log"
            await guest(f"rm -f {status_path} {log_path}", kind=f"{label}-cleanup")
            rc = await guest(
                "RESIDUAL_SCOPE_LABEL=" + shlex.quote(label)
                + " RESIDUAL_SCOPE_LIMIT=" + shlex.quote(str(limit))
                + " RESIDUAL_SCOPE_SLEEP=" + shlex.quote(repr(args.sleep_seconds))
                + " python3 -u -c " + shlex.quote(PROBE_CODE)
                + f" >/tmp/residual-scope-{label}.stdout 2>&1",
                kind=f"{label}-probe",
                expect_zero=False,
                timeout=max(240000, int(limit * args.sleep_seconds * 4000 + 120000)),
            )
            status_exit, state = await process_state(label)
            await guest(
                f"printf 'SCOPE_STATUS_{label} '; cat {status_path} 2>/dev/null || echo MISSING; "
                f"printf 'SCOPE_LOG_{label}_BEGIN\\n'; cat {log_path} 2>/dev/null || true; printf 'SCOPE_LOG_{label}_END\\n'; "
                f"test ! -e {WORKER_PID}",
                kind=f"{label}-evidence",
            )
            result = {
                "label": label,
                "iterations_requested": limit,
                "process_exit": rc,
                "status_exit": status_exit,
                "state": state,
            }
            report["processes"].append(result)
            return result

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
            await guest(f"test ! -e {WORKER_PID}", kind="precondition")

            results = []
            for label, limit in PLANS[args.plan]:
                results.append(await run_process(label, limit))
                if results[-1]["state"] != "PASS":
                    break

            if args.plan == "single-273":
                first = results[0]
                if first["state"] == "FAIL":
                    report["classification"] = "SINGLE_PROCESS_POSITIVE_SLEEP_FAILURE_REPRODUCED"
                elif first["state"] == "PASS":
                    report["classification"] = "SINGLE_PROCESS_BOUNDARY_NOT_REPRODUCED"
                    report["status"] = "PASS"
                else:
                    report["classification"] = "SINGLE_PROCESS_INCONCLUSIVE"
            else:
                if len(results) == 1 and results[0]["state"] != "PASS":
                    report["classification"] = "FIRST_PROCESS_FAILED_BELOW_KNOWN_BOUNDARY"
                elif len(results) == 2 and results[1]["state"] == "FAIL":
                    report["classification"] = "SECOND_PROCESS_FAILED_BELOW_OWN_BOUNDARY_SHARED_STATE_EVIDENCE"
                elif len(results) == 2 and all(r["state"] == "PASS" for r in results):
                    report["classification"] = "FRESH_PROCESS_RESETS_OR_AVOIDS_SLEEP_BOUNDARY"
                    report["status"] = "PASS"
                else:
                    report["classification"] = "PROCESS_SCOPE_INCONCLUSIVE"
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
            print("WEBVM_SLEEP_SCOPE_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    raise SystemExit(asyncio.run(main()))
