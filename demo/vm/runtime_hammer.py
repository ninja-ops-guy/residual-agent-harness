#!/usr/bin/env python3
"""Minimal published-WebVM Python process hammer for issue #120.

This deliberately avoids Mission Control and provider flows. It launches the
published guest, repeatedly starts fresh Python processes through the existing
terminal, and fails on the first stdlib/runtime anomaly. The objective is to
separate generic CheerpX/WebVM process/runtime instability from workload-induced
RESIDUAL behavior.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import secrets
import time
from pathlib import Path

from playwright.async_api import async_playwright

PROMPT = "residual@demo:~/residual-agent-harness$"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("--count must be 1..1000")
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "residual.webvm-python-hammer.v1",
        "expected_sha": args.expected_sha,
        "count_requested": args.count,
        "status": "FAIL",
        "cloud_inference": "NOT_RUN",
    }
    started = time.monotonic()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)[:2000]))
        try:
            info_url = args.url.rstrip("/") + "/build-info.json"
            info = await context.request.get(info_url, timeout=30000)
            assert info.ok, f"build-info HTTP {info.status}"
            identity = await info.json()
            report["build_identity"] = identity
            assert identity.get("commit") == args.expected_sha, "published revision changed"

            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_function(
                "p => document.body.innerText.replace(/\\s/g,'').includes(p.replace(/\\s/g,''))",
                arg=PROMPT,
                timeout=120000,
            )
            await page.locator("#mc-terminal").click()
            await page.locator(".xterm-helper-textarea").focus()

            nonce = secrets.token_hex(8)
            marker = f"RESIDUAL_HAMMER_{nonce}:"
            # Each loop iteration starts a fresh CPython process and exercises the
            # two stdlib surfaces that have failed in retained production evidence:
            # re._parser object construction and SHA-512 import/use. No RESIDUAL
            # module is imported here.
            py = (
                "import hashlib,re,uuid,platform,_sha512; "
                "from re import _parser; "
                "p=_parser.SubPattern(_parser.State(),[]); "
                "assert re.compile(r'(ab|cd)+[0-9]{2}').fullmatch('ab12'); "
                "assert len(hashlib.sha512(b'residual').digest())==64; "
                "assert str(uuid.UUID(int=0))=='00000000-0000-0000-0000-000000000000'; "
                "platform.python_implementation()"
            )
            # The completion marker is deliberately assembled from two nonce
            # halves in the guest. That prevents the echoed shell command itself
            # from satisfying Playwright's completion wait before the loop runs.
            command = (
                f"i=0; hammer_rc=0; while [ $i -lt {args.count} ]; do "
                f"python3 -c \"{py}\" >/dev/null 2>/tmp/residual-hammer.err || {{ "
                "hammer_rc=$?; echo HAMMER_FAIL_INDEX=$i RC=$hammer_rc; "
                "cat /tmp/residual-hammer.err; break; }; "
                "i=$((i+1)); done; "
                "if [ $hammer_rc -eq 0 ]; then echo HAMMER_PASS_COUNT=$i; fi; "
                "printf '\\nRESIDUAL_HAMMER_%s%s:%s\\n' '"
                + nonce[:8]
                + "' '"
                + nonce[8:]
                + "' \"$hammer_rc\""
            )
            await page.keyboard.press("Control+u")
            await page.keyboard.type(command, delay=0)
            await page.keyboard.press("Enter")
            await page.wait_for_function(
                "m => document.body.innerText.replace(/\\s/g,'').includes(m)",
                arg=marker,
                timeout=600000,
            )
            body = await page.locator("body").inner_text()
            compact = re.sub(r"\s", "", body)
            match = re.search(re.escape(marker) + r"(\d+)", compact)
            assert match is not None, "hammer exit marker missing"
            rc = int(match.group(1))
            report["exit_status"] = rc
            pass_match = re.search(r"HAMMER_PASS_COUNT=(\d+)", body)
            fail_match = re.search(r"HAMMER_FAIL_INDEX=(\d+)", body)
            if pass_match:
                report["count_completed"] = int(pass_match.group(1))
            if fail_match:
                report["failure_index"] = int(fail_match.group(1))
            report["terminal_tail"] = body[-20000:]
            if rc != 0:
                raise AssertionError(f"fresh-Python hammer failed with exit {rc}")
            assert report.get("count_completed") == args.count, "hammer did not complete requested count"
            assert not errors, "browser page error during hammer"
            report["status"] = "PASS"
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
            try:
                report["terminal_tail"] = (await page.locator("body").inner_text())[-20000:]
            except Exception:
                pass
        finally:
            report["page_errors"] = errors
            report["elapsed_seconds"] = round(time.monotonic() - started, 2)
            try:
                await page.screenshot(path=str(args.output / "hammer-final.png"), timeout=5000)
            except Exception:
                pass
            try:
                await context.tracing.stop(path=str(args.output / "hammer-trace.zip"))
            finally:
                await browser.close()
            (args.output / "hammer-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("WEBVM_HAMMER_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
