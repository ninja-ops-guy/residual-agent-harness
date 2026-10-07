#!/usr/bin/env python3
"""Compare long-lived WebVM execution with explicit guest/page recycle.

This is diagnostic-only. It never authenticates to a paid provider and never
retries a failed command. A recycle is an explicit lifecycle boundary: the
browser page/JS context is replaced, then persisted RESIDUAL mission evidence
and browser conversation identity must still be available before execution
continues.
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
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--recycle", action="store_true")
    parser.add_argument("--boot-timeout", type=int, default=120)
    args = parser.parse_args()
    if args.cycles < 1 or args.cycles > 40:
        parser.error("--cycles must be between 1 and 40")

    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "residual.webvm-recycle-diagnostic.v1",
        "url": safe_url(args.url),
        "expected_sha": args.expected_sha,
        "cycles_requested": args.cycles,
        "recycle_between_cycles": args.recycle,
        "status": "FAIL",
        "cycles": [],
        "errors": [],
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
            return text[-10000:]

        async def run_guest(command: str, *, label: str) -> int:
            nonce = secrets.token_hex(8)
            prefix = f"RESIDUAL_RECYCLE_{nonce}:"
            wire = (
                command
                + "; recycle_rc=$?; printf '\\nRESIDUAL_RECYCLE_%s%s:%s\\n' '"
                + nonce[:8]
                + "' '"
                + nonce[8:]
                + "' \"$recycle_rc\""
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
                raise AssertionError(f"guest marker disappeared at {label}")
            code = int(match[1])
            if code != 0:
                raise AssertionError(
                    f"guest command failed at {label} with exit {code}: {command}\n{await terminal_tail()}"
                )
            return code

        python_probe = (
            "python3 -c \"import hashlib,re,uuid,platform,_sha512; from re import _parser; "
            "p=_parser.SubPattern(_parser.State(),[]); "
            "assert re.compile(r'(ab|cd)+[0-9]{2}').fullmatch('ab12'); "
            "assert len(hashlib.sha512(b'residual').digest())==64; "
            "assert str(uuid.UUID(int=0))=='00000000-0000-0000-0000-000000000000'; "
            "platform.python_implementation()\""
        )

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
            assert await page.evaluate("window.crossOriginIsolated"), "guest page is not cross-origin isolated"

            # Create one real Mission Control audit whose evidence must survive
            # every explicit recycle. This exercises the same persisted run tree
            # and browser conversation state used by the public demo.
            await page.locator("#mc-mission").click()
            await page.get_by_text("Run controls", exact=True).click()
            await page.locator("#mc-mode").select_option("audit")
            prompt = "Recycle persistence audit " + secrets.token_hex(4)
            await page.locator("#mc-prompt").fill(prompt)
            await page.locator("#mc-files").fill("residual/cli.py")
            await page.locator("#mc-run").click()
            await page.wait_for_function(
                "() => document.querySelector('#mc-verdict').textContent.startsWith('PASSED') && !document.querySelector('#mc-result').hidden",
                timeout=120000,
            )
            mission_path_text = await page.locator("#mc-path").inner_text()
            mission_path_match = re.search(r"/opt/residual/runs/missions/m-[a-f0-9]{32}", mission_path_text)
            assert mission_path_match is not None, "mission path missing"
            mission_path = mission_path_match.group()
            conversation_id = await page.evaluate("localStorage.getItem('residual.chat.current.v2')")
            assert re.fullmatch(r"c-[a-f0-9]{32}", conversation_id or ""), "conversation identity missing"
            report["mission_path"] = mission_path
            report["conversation_id"] = conversation_id

            persistence_check = (
                f"test -s {mission_path}/trace.jsonl && test -s {mission_path}/result.json && "
                f"python3 -m residual verify-trace {mission_path}/trace.jsonl --result {mission_path}/result.json >/dev/null"
            )

            for cycle in range(1, args.cycles + 1):
                cycle_started = time.monotonic()
                await run_guest(python_probe, label=f"cycle-{cycle}-python-pre")
                await run_guest(
                    "python3 -m residual.workbench audit --stream --files residual/cli.py >/dev/null",
                    label=f"cycle-{cycle}-audit",
                )
                await run_guest(python_probe, label=f"cycle-{cycle}-python-post")
                await run_guest(persistence_check, label=f"cycle-{cycle}-evidence")

                cycle_record = {
                    "cycle": cycle,
                    "recycled": False,
                    "elapsed_seconds": round(time.monotonic() - cycle_started, 2),
                }

                if args.recycle and cycle < args.cycles:
                    # A page reload is an explicit lifecycle action, not retry.
                    # Prove the page/JS execution context was replaced, then prove
                    # authoritative run evidence and browser-local conversation
                    # identity survived before allowing the next command.
                    sentinel = "recycle-" + secrets.token_hex(8)
                    await page.evaluate("value => { window.__residualRecycleSentinel = value; }", sentinel)
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                    await wait_guest()
                    assert await page.evaluate("window.__residualRecycleSentinel === undefined"), "page JS context did not reset"
                    restored_conversation = await page.evaluate("localStorage.getItem('residual.chat.current.v2')")
                    assert restored_conversation == conversation_id, "conversation identity did not survive recycle"
                    await run_guest(persistence_check, label=f"cycle-{cycle}-post-recycle-evidence")
                    await run_guest(python_probe, label=f"cycle-{cycle}-post-recycle-python")
                    await page.locator("#mc-mission").click()
                    chat_text = await page.locator("#mc-chat").inner_text()
                    assert prompt in chat_text, "conversation transcript did not survive recycle"
                    cycle_record["recycled"] = True
                    cycle_record["post_recycle_state"] = "PASS"

                report["cycles"].append(cycle_record)
                report["cycles_completed"] = cycle
                print(
                    f"WEBVM_RECYCLE_PROGRESS: cycle={cycle} recycle={args.recycle}",
                    flush=True,
                )

            assert not report["errors"], "unhandled browser JavaScript error"
            report["status"] = "PASS"
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
        finally:
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
            print("WEBVM_RECYCLE_REPORT: " + json.dumps(report), flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
