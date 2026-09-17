#!/usr/bin/env python3
"""Compare libc sleep wrappers with Python time.sleep inside the published WebVM guest."""
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
STATUS = "/tmp/residual-libc-sleep.status"
LOG = "/tmp/residual-libc-sleep.log"

PROBE_CODE = r'''
import ctypes, os, pathlib, time

mode = os.environ["RESIDUAL_LIBC_MODE"]
limit = int(os.environ.get("RESIDUAL_LIBC_LIMIT", "300"))
sleep_s = float(os.environ.get("RESIDUAL_LIBC_SLEEP", "0.05"))
status = pathlib.Path("/tmp/residual-libc-sleep.status")
log_path = pathlib.Path("/tmp/residual-libc-sleep.log")

CLOCK_MONOTONIC = 1
TIMER_ABSTIME = 1
NR_CLOCK_GETTIME32 = 265

class Timespec32(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
libc.clock_nanosleep.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(Timespec32), ctypes.c_void_p]
libc.clock_nanosleep.restype = ctypes.c_int
libc.nanosleep.argtypes = [ctypes.POINTER(Timespec32), ctypes.POINTER(Timespec32)]
libc.nanosleep.restype = ctypes.c_int


def raw_gettime():
    ts = Timespec32()
    ctypes.set_errno(0)
    rc = int(libc.syscall(ctypes.c_long(NR_CLOCK_GETTIME32), ctypes.c_int(CLOCK_MONOTONIC), ctypes.byref(ts)))
    return rc, ctypes.get_errno(), int(ts.tv_sec), int(ts.tv_nsec)


def add_duration(sec, nsec, duration):
    nsec += int(round(duration * 1_000_000_000))
    sec += nsec // 1_000_000_000
    nsec %= 1_000_000_000
    return sec, nsec


def wrapper_wait(absolute):
    if absolute:
        grc, gerr, sec, nsec = raw_gettime()
        if grc != 0:
            return {"stage": "gettime", "rc": grc, "errno": gerr, "sec": sec, "nsec": nsec}
        sec, nsec = add_duration(sec, nsec, sleep_s)
    else:
        sec = int(sleep_s)
        nsec = int(round((sleep_s - sec) * 1_000_000_000))
    req = Timespec32(sec, nsec)
    ctypes.set_errno(0)
    rc = int(libc.clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME if absolute else 0, ctypes.byref(req), None))
    return {"stage": "clock_nanosleep", "rc": rc, "errno": ctypes.get_errno(), "sec": sec, "nsec": nsec}


def nanosleep_wait():
    sec = int(sleep_s)
    nsec = int(round((sleep_s - sec) * 1_000_000_000))
    req = Timespec32(sec, nsec)
    rem = Timespec32()
    ctypes.set_errno(0)
    rc = int(libc.nanosleep(ctypes.byref(req), ctypes.byref(rem)))
    return {"stage": "nanosleep", "rc": rc, "errno": ctypes.get_errno(), "sec": sec, "nsec": nsec, "rem_sec": int(rem.tv_sec), "rem_nsec": int(rem.tv_nsec)}


def validate_abi():
    rc, err, sec, nsec = raw_gettime()
    py = time.monotonic()
    raw = sec + nsec / 1_000_000_000
    return rc == 0 and 0 <= nsec < 1_000_000_000 and abs(raw - py) < 5, {"rc": rc, "errno": err, "sec": sec, "nsec": nsec, "raw": raw, "python_monotonic": py, "delta": raw - py}

abi_ok, abi_info = validate_abi()
count = 0
with log_path.open("w", encoding="utf-8", buffering=1) as log:
    log.write(f"START pid={os.getpid()} mode={mode} limit={limit} sleep_s={sleep_s!r} sizeof_long={ctypes.sizeof(ctypes.c_long)} sizeof_timespec={ctypes.sizeof(Timespec32)} abi={abi_info!r}\n")
    if not abi_ok:
        line = f"UNSUPPORTED mode={mode} reason=legacy_timespec_validation_failed abi={abi_info!r}\n"
        log.write(line); status.write_text(line, encoding="utf-8"); raise SystemExit(90)
    try:
        for count in range(1, limit + 1):
            if mode == "clock-rel":
                result = wrapper_wait(False)
                failed = result["rc"] != 0
            elif mode == "clock-abs":
                result = wrapper_wait(True)
                failed = result["rc"] != 0
            elif mode == "nanosleep-rel":
                result = nanosleep_wait()
                failed = result["rc"] != 0
            elif mode == "python-sleep":
                try:
                    time.sleep(sleep_s)
                except BaseException as exc:
                    result = {"stage": "python_time_sleep", "exception": type(exc).__name__, "message": str(exc)}
                    failed = True
                else:
                    result = {"stage": "python_time_sleep", "rc": 0}
                    failed = False
            else:
                raise RuntimeError("unknown mode: " + mode)
            if count % 50 == 0 or count in (1, 250, 270, 271, 272, 273, 274, 275):
                log.write(f"STEP count={count} result={result!r}\n")
            if failed:
                line = f"FAIL mode={mode} count={count} result={result!r} python_monotonic={time.monotonic()!r}\n"
                log.write(line); status.write_text(line, encoding="utf-8"); raise SystemExit(80)
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        line = f"ERROR mode={mode} count={count} type={type(exc).__name__} message={str(exc).replace(chr(10),' ')[:500]}\n"
        log.write(line); status.write_text(line, encoding="utf-8"); raise
    else:
        line = f"PASS mode={mode} count={count} python_monotonic={time.monotonic()!r}\n"
        log.write(line); status.write_text(line, encoding="utf-8")
'''


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("clock-rel", "clock-abs", "nanosleep-rel", "python-sleep"), required=True)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    parser.add_argument("--boot-timeout", type=int, default=120)
    args = parser.parse_args()
    if not 50 <= args.iterations <= 1000:
        parser.error("--iterations must be 50..1000")
    if not 0 < args.sleep_seconds <= 1:
        parser.error("--sleep-seconds must be >0 and <=1")
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "residual.webvm-runtime-libc-sleep-wrapper.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "mode": args.mode,
        "iterations_requested": args.iterations,
        "sleep_seconds": args.sleep_seconds,
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
            return value[-18000:]

        async def guest(command: str, *, kind: str, expect_zero: bool = True, timeout: int = 300000) -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_LIBCSLEEP_{nonce}:"
            wire = command + "; rc=$?; printf '\\nRESIDUAL_LIBCSLEEP_%s%s:%s\\n' '" + nonce[:8] + "' '" + nonce[8:] + "' \"$rc\""
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
            report["commands"].append({"kind": kind, "exit_status": rc, "elapsed_seconds": round(time.monotonic() - started, 2), "terminal_tail": await terminal_tail()})
            if expect_zero and rc:
                raise AssertionError(f"guest command failed with exit {rc}: {command}")
            return rc

        async def status_code() -> int:
            return await guest(
                f"if grep -q '^PASS ' {STATUS} 2>/dev/null; then (exit 41); elif grep -q '^FAIL ' {STATUS} 2>/dev/null; then (exit 42); elif grep -q '^UNSUPPORTED ' {STATUS} 2>/dev/null; then (exit 43); elif grep -q '^ERROR ' {STATUS} 2>/dev/null; then (exit 44); else (exit 45); fi",
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

            probe_rc = await guest(
                "RESIDUAL_LIBC_MODE=" + shlex.quote(args.mode)
                + " RESIDUAL_LIBC_LIMIT=" + shlex.quote(str(args.iterations))
                + " RESIDUAL_LIBC_SLEEP=" + shlex.quote(repr(args.sleep_seconds))
                + " python3 -u -c " + shlex.quote(PROBE_CODE)
                + " >/tmp/residual-libc-sleep.stdout 2>&1",
                kind="libc-wrapper-probe",
                expect_zero=False,
                timeout=max(300000, int(args.iterations * args.sleep_seconds * 4000 + 180000)),
            )
            state = await status_code()
            report["probe_process_exit"] = probe_rc
            report["status_exit"] = state
            await guest(
                f"printf 'LIBC_SLEEP_STATUS '; cat {STATUS} 2>/dev/null || echo MISSING; printf 'LIBC_SLEEP_LOG_BEGIN\\n'; cat {LOG} 2>/dev/null || true; printf 'LIBC_SLEEP_LOG_END\\n'; test ! -e {WORKER_PID}",
                kind="evidence",
            )
            if state == 41 and probe_rc == 0:
                report["classification"] = "WRAPPER_BOUNDED_PASS"
                report["status"] = "PASS"
            elif state == 42:
                report["classification"] = "WRAPPER_OR_PYTHON_SLEEP_FAILURE"
            elif state == 43:
                report["classification"] = "WRAPPER_SURFACE_UNSUPPORTED_OR_ABI_INVALID"
            elif state == 44:
                report["classification"] = "WRAPPER_PROBE_ERROR"
            else:
                report["classification"] = "WRAPPER_RESULT_INCONSISTENT"
        except Exception as exc:
            report["failure"] = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                report["page_state"] = await page.evaluate("({url:location.pathname,isolated:window.crossOriginIsolated,controlled:!!navigator.serviceWorker.controller,body:document.body.innerText.slice(-20000)})")
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
            print("WEBVM_LIBC_SLEEP_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    raise SystemExit(asyncio.run(main()))
