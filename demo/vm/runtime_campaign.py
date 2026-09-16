#!/usr/bin/env python3
"""Stress and classify long-lived WebVM guest Python/runtime instability.

This diagnostic never authenticates to a paid provider. It drives the existing
Mission Control acceptance sequence against an already-published WebVM artifact,
adds non-mutating shell/Python integrity probes around guest commands, and stops
on the first runtime failure while retaining the pre-failure evidence.
"""
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

from mission_smoke import workbench_acceptance
from pages_contract import validate_entry_html

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
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--boot-timeout", type=int, default=120)
    args = parser.parse_args()
    if args.iterations < 1 or args.iterations > 12:
        parser.error("--iterations must be between 1 and 12")

    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "residual.webvm-runtime-diagnostic.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "iterations_requested": args.iterations,
        "status": "FAIL",
        "stages": [],
        "commands": [],
        "probes": [],
        "errors": [],
        "failed_requests": [],
        "http_errors": [],
        "optional_requests": [],
        "console": [],
        "cloud_inference": "NOT_RUN",
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
            if len(report["console"]) < 200
            else None,
        )
        context.on(
            "requestfailed",
            lambda req: report["failed_requests"].append({"url": safe_url(req.url), "error": req.failure})
            if len(report["failed_requests"]) < 200
            else None,
        )
        context.on(
            "response",
            lambda res: report["http_errors"].append({"url": safe_url(res.url), "status": res.status})
            if res.status >= 400 and len(report["http_errors"]) < 200
            else None,
        )
        context.on(
            "request",
            lambda req: report["optional_requests"].append(safe_url(req.url))
            if urlsplit(req.url).hostname in {"plausible.leaningtech.com", "js.puter.com", "api.puter.com"}
            else None,
        )

        async def stage(name: str) -> None:
            record = {"name": name, "elapsed_seconds": round(time.monotonic() - started, 2)}
            report["stages"].append(record)
            print(f"WEBVM_DIAGNOSTIC_STAGE: {name}", flush=True)

        async def wait_text(text: str, timeout: int = 120000) -> None:
            await page.wait_for_function(
                "text => document.body.innerText.replace(/\\s/g,'').includes(text.replace(/\\s/g,''))",
                arg=text,
                timeout=timeout,
            )

        async def wait_guest() -> None:
            await wait_text(BOOT, timeout=args.boot_timeout * 1000)
            await wait_text(PROMPT, timeout=args.boot_timeout * 1000)

        async def terminal_tail() -> str:
            try:
                text = await page.locator(".xterm-rows").inner_text(timeout=5000)
            except Exception:
                text = await page.locator("body").inner_text(timeout=5000)
            return text[-12000:]

        async def run_guest(command: str, *, expect_zero: bool = True, kind: str = "command") -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_DIAG_{nonce}:"
            wire = (
                command
                + "; diag_rc=$?; printf '\\nRESIDUAL_DIAG_%s%s:%s\\n' '"
                + nonce[:8]
                + "' '"
                + nonce[8:]
                + "' \"$diag_rc\""
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
                raise AssertionError("guest diagnostic exit marker disappeared")
            code = int(match[1])
            record = {
                "kind": kind,
                "command": command,
                "exit_status": code,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "terminal_tail": await terminal_tail(),
            }
            report["commands"].append(record)
            if expect_zero and code != 0:
                raise AssertionError(f"Guest command failed with exit {code}: {command}")
            return code

        async def probe(label: str, *, tolerate_python_failure: bool = False) -> None:
            shell_command = (
                "printf 'RUNTIME_PROBE_LABEL=%s\\n' '" + label + "'; "
                "sha256sum /usr/lib/python3.11/re/_parser.py "
                "/usr/lib/python3.11/re/_compiler.py /usr/lib/python3.11/hashlib.py "
                "/usr/lib/python3.11/uuid.py /usr/lib/python3.11/platform.py; "
                "find /usr/lib/python3.11/lib-dynload -maxdepth 1 -name '_sha512*.so' -print0 "
                "| xargs -0 -r sha256sum; "
                "printf 'MEMINFO '; awk '/MemFree:|MemAvailable:|SwapFree:/{printf \"%s=%s \", $1, $2} END{print \"\"}' /proc/meminfo; "
                "printf 'FILESYSTEM '; df -Pk / /opt/residual | tail -n +2 | tr '\\n' ';'; echo"
            )
            shell_rc = await run_guest(shell_command, kind="probe-shell")
            python_command = (
                "python3 -c \"import hashlib,re,uuid,platform,_sha512,sys; "
                "from re import _parser; "
                "p=_parser.SubPattern(_parser.State(),[]); "
                "assert re.compile(r'(ab|cd)+[0-9]{2}').fullmatch('ab12'); "
                "assert len(hashlib.sha512(b'residual').digest())==64; "
                "assert str(uuid.UUID(int=0))=='00000000-0000-0000-0000-000000000000'; "
                "print('PY_RUNTIME_OK',sys.version.split()[0],"
                "hashlib.sha256(_parser.SubPattern.__init__.__code__.co_code).hexdigest(),"
                "hashlib.sha256(_parser.SubPattern.__getitem__.__code__.co_code).hexdigest(),"
                "platform.python_implementation())\""
            )
            python_rc = await run_guest(
                python_command,
                expect_zero=not tolerate_python_failure,
                kind="probe-python",
            )
            report["probes"].append(
                {
                    "label": label,
                    "shell_exit_status": shell_rc,
                    "python_exit_status": python_rc,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                }
            )
            if python_rc != 0 and not tolerate_python_failure:
                raise AssertionError(f"Python runtime probe failed at {label}")

        command_sequence = 0

        async def instrumented_command_proof(command: str) -> None:
            nonlocal command_sequence
            command_sequence += 1
            label = f"command-{command_sequence}"
            await probe(label + "-pre")
            await run_guest(command, kind="workbench-proof")
            await probe(label + "-post")

        try:
            response = await context.request.get(args.url, timeout=30000)
            assert response.ok, f"entry HTTP {response.status}"
            entry = await response.body()
            validate_entry_html(entry.decode("utf-8"))
            info = await context.request.get(args.url.rstrip("/") + "/build-info.json", timeout=30000)
            assert info.ok, f"build identity HTTP {info.status}"
            identity = await info.json()
            report["build_identity"] = identity
            assert identity.get("commit") == args.expected_sha, "served commit differs from expected commit"
            assert hashlib.sha256(entry).hexdigest() == identity["files"]["index.html"], "served entry hash mismatch"

            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await wait_guest()
            await stage("guest_attached_and_shell_ready")
            await page.locator("#mc-terminal").click()
            assert await page.evaluate("window.crossOriginIsolated"), "guest page is not cross-origin isolated"
            assert await page.evaluate("window.top === window"), "WebVM is not top-level"
            await probe("baseline")

            for iteration in range(1, args.iterations + 1):
                if iteration > 1:
                    await page.locator("#mc-mission").click()
                    if await page.locator("#mc-new-chat").is_enabled():
                        await page.locator("#mc-new-chat").click()
                await stage(f"iteration_{iteration}_start")
                await workbench_acceptance(
                    page,
                    context,
                    args,
                    report,
                    instrumented_command_proof,
                    stage,
                )
                await probe(f"iteration-{iteration}-complete")
                await stage(f"iteration_{iteration}_complete")
                report["iterations_completed"] = iteration

            assert not report["errors"], "unhandled browser JavaScript error"
            report["status"] = "PASS"
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
            try:
                await probe("after-failure", tolerate_python_failure=True)
            except Exception as probe_error:
                report["post_failure_probe_error"] = f"{type(probe_error).__name__}: {probe_error}"
        finally:
            try:
                report["page_state"] = await page.evaluate(
                    "({url:location.pathname, isolated:window.crossOriginIsolated, controlled:!!navigator.serviceWorker.controller, title:document.title, body:document.body.innerText.slice(-20000)})"
                )
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
            print("WEBVM_DIAGNOSTIC_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
