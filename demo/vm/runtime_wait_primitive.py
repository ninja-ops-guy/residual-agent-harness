#!/usr/bin/env python3
"""Discriminate Python time.sleep from a pure-stdlib select timeout in published WebVM.

This diagnostic does not touch Mission Control runtime code and never authenticates
to a cloud provider. It runs each wait primitive in a fresh guest CPython process,
retains the known positive-time.sleep failure as raw evidence, and only classifies
the alternate primitive if the exact published main revision is bound first.
"""
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
STATUS_PREFIX = "/tmp/residual-wait-primitive"
LOG_PREFIX = "/tmp/residual-wait-primitive"

PROBE_CODE = r'''
import os, pathlib, select, time

mode = os.environ["RESIDUAL_WAIT_MODE"]
limit = int(os.environ["RESIDUAL_WAIT_LIMIT"])
wait_s = float(os.environ.get("RESIDUAL_WAIT_SECONDS", "0.05"))
status = pathlib.Path(os.environ["RESIDUAL_WAIT_STATUS"])
log_path = pathlib.Path(os.environ["RESIDUAL_WAIT_LOG"])

count = 0
with log_path.open("w", encoding="utf-8", buffering=1) as log:
    log.write(f"START pid={os.getpid()} mode={mode} limit={limit} wait_s={wait_s!r}\n")
    try:
        for count in range(1, limit + 1):
            if mode == "python-sleep":
                time.sleep(wait_s)
            elif mode == "select-empty":
                ready = select.select([], [], [], wait_s)
                if ready != ([], [], []):
                    raise RuntimeError(f"unexpected select readiness: {ready!r}")
            else:
                raise RuntimeError("unknown mode: " + mode)
            if count % 50 == 0 or count in (1, 250, 270, 271, 272, 273, 274, 275):
                log.write(f"STEP mode={mode} count={count} monotonic={time.monotonic()!r}\n")
    except BaseException as exc:
        line = (
            f"FAIL mode={mode} count={count} type={type(exc).__name__} "
            f"message={str(exc).replace(chr(10), ' ')[:300]} monotonic={time.monotonic()!r}\n"
        )
        log.write(line)
        status.write_text(line, encoding="utf-8")
        raise SystemExit(80)
    else:
        line = f"PASS mode={mode} count={count} monotonic={time.monotonic()!r}\n"
        log.write(line)
        status.write_text(line, encoding="utf-8")
'''


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    parser.add_argument("--control-iterations", type=int, default=300)
    parser.add_argument("--candidate-iterations", type=int, default=400)
    parser.add_argument("--boot-timeout", type=int, default=120)
    args = parser.parse_args()
    if not 0 < args.sleep_seconds <= 1:
        parser.error("--sleep-seconds must be >0 and <=1")
    if not 273 <= args.control_iterations <= 1000:
        parser.error("--control-iterations must be 273..1000")
    if not 300 <= args.candidate_iterations <= 2000:
        parser.error("--candidate-iterations must be 300..2000")

    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "residual.webvm-runtime-wait-primitive.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "sleep_seconds": args.sleep_seconds,
        "control_iterations": args.control_iterations,
        "candidate_iterations": args.candidate_iterations,
        "mission_control_worker": "MUST_REMAIN_ABSENT",
        "cloud_inference": "NOT_RUN",
        "status": "FAIL",
        "classification": "UNCLASSIFIED",
        "arms": {},
        "commands": [],
        "claim_boundary": (
            "A discriminator PASS only shows that select.select([],[],[],timeout) avoids the retained "
            "positive time.sleep call-273 symptom in this bounded published-main run. It is not a "
            "production-reliability, root-cause, provider-quality, or long-run qualification claim."
        ),
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

        async def guest(command: str, *, kind: str, expect_zero: bool = True, timeout: int = 300000):
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_WAIT_{nonce}:"
            wire = (
                command
                + "; rc=$?; printf '\\nRESIDUAL_WAIT_%s%s:%s\\n' '"
                + nonce[:8]
                + "' '"
                + nonce[8:]
                + "' \"$rc\""
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
            tail = await terminal_tail()
            report["commands"].append(
                {
                    "kind": kind,
                    "exit_status": rc,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                    "terminal_tail": tail,
                }
            )
            if expect_zero and rc:
                raise AssertionError(f"guest command failed with exit {rc}: {command}")
            return rc, tail

        async def run_arm(mode: str, iterations: int):
            slug = mode.replace("-", "_")
            status = f"{STATUS_PREFIX}-{slug}.status"
            log = f"{LOG_PREFIX}-{slug}.log"
            await guest(f"rm -f {status} {log}; test ! -e {WORKER_PID}", kind=f"{mode}-precondition")
            process_rc, _ = await guest(
                "RESIDUAL_WAIT_MODE=" + shlex.quote(mode)
                + " RESIDUAL_WAIT_LIMIT=" + shlex.quote(str(iterations))
                + " RESIDUAL_WAIT_SECONDS=" + shlex.quote(repr(args.sleep_seconds))
                + " RESIDUAL_WAIT_STATUS=" + shlex.quote(status)
                + " RESIDUAL_WAIT_LOG=" + shlex.quote(log)
                + " python3 -u -c " + shlex.quote(PROBE_CODE)
                + " >/tmp/residual-wait-primitive.stdout 2>&1",
                kind=f"{mode}-process",
                expect_zero=False,
                timeout=max(300000, int(iterations * args.sleep_seconds * 4000 + 180000)),
            )
            state_rc, _ = await guest(
                f"if grep -q '^PASS ' {status} 2>/dev/null; then (exit 41); "
                f"elif grep -q '^FAIL ' {status} 2>/dev/null; then (exit 42); else (exit 45); fi",
                kind=f"{mode}-status",
                expect_zero=False,
            )
            _, evidence = await guest(
                f"printf 'WAIT_STATUS '; cat {status} 2>/dev/null || echo MISSING; "
                f"printf 'WAIT_LOG_BEGIN\\n'; cat {log} 2>/dev/null || true; "
                f"printf 'WAIT_LOG_END\\n'; test ! -e {WORKER_PID}",
                kind=f"{mode}-evidence",
            )
            result = {
                "process_exit": process_rc,
                "status_exit": state_rc,
            }
            if mode == "python-sleep":
                result["expected_failure_observed"] = bool(
                    process_rc == 80
                    and state_rc == 42
                    and re.search(r"FAIL mode=python-sleep count=273 type=OverflowError", evidence)
                )
            else:
                result["candidate_pass_observed"] = bool(
                    process_rc == 0
                    and state_rc == 41
                    and re.search(rf"PASS mode={re.escape(mode)} count={iterations}\b", evidence)
                )
            report["arms"][mode] = result
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
            await guest(f"test ! -e {WORKER_PID}", kind="global-precondition")

            control = await run_arm("python-sleep", args.control_iterations)
            candidate = await run_arm("select-empty", args.candidate_iterations)

            if control.get("expected_failure_observed") and candidate.get("candidate_pass_observed"):
                report["classification"] = "SELECT_EMPTY_AVOIDS_PYTHON_SLEEP_CALL273_BOUNDARY"
                report["status"] = "PASS"
            elif not control.get("expected_failure_observed"):
                report["classification"] = "CONTROL_DID_NOT_REPRODUCE_EXPECTED_SLEEP_BOUNDARY"
            elif not candidate.get("candidate_pass_observed"):
                report["classification"] = "SELECT_EMPTY_DID_NOT_CLEAR_BOUNDARY"
            else:
                report["classification"] = "DISCRIMINATOR_INCONSISTENT"
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
            print("WEBVM_WAIT_PRIMITIVE_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
