#!/usr/bin/env python3
"""Prove the iOS WebKit preflight escapes before heavyweight WebVM boot."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import async_playwright

IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 "
    "Mobile/15E148 Safari/604.1"
)


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "entry": safe_url(args.url),
        "browser": "webkit",
        "profile": "iphone-safari-compatible-ua",
        "status": "FAIL",
        "requests": [],
        "page_errors": [],
        "http_errors": [],
    }

    async with async_playwright() as pw:
        browser = await pw.webkit.launch()
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent=IPHONE_UA,
            has_touch=True,
            is_mobile=True,
        )
        page = await context.new_page()

        def on_request(request) -> None:
            if len(report["requests"]) < 200:
                report["requests"].append(safe_url(request.url))

        page.on("request", on_request)
        page.on("pageerror", lambda error: report["page_errors"].append(str(error)[:2000]))
        page.on(
            "response",
            lambda response: report["http_errors"].append(
                {"url": safe_url(response.url), "status": response.status}
            )
            if response.status >= 400 and len(report["http_errors"]) < 50
            else None,
        )

        try:
            await page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_function(
                """() => location.pathname.endsWith('/walkthrough/') &&
                new URLSearchParams(location.search).get('platform') === 'ios-webkit'""",
                timeout=15000,
            )
            final = urlsplit(page.url)
            report["final_url"] = safe_url(page.url)
            report["final_query"] = parse_qs(final.query)
            body = await page.locator("body").inner_text()
            assert "RESIDUAL / ENGINEER WALKTHROUGH" in body, "walkthrough marker missing"

            heavy = [
                url for url in report["requests"]
                if "residual-demo-" in url or ".ext2" in url
            ]
            report["heavy_vm_requests"] = heavy
            assert not heavy, f"heavy WebVM disk request escaped iOS preflight: {heavy[:3]}"
            assert not report["page_errors"], f"WebKit page error: {report['page_errors'][:1]}"
            report["status"] = "PASS"
        except Exception as error:
            report["failure"] = f"{type(error).__name__}: {error}"
        finally:
            try:
                await page.screenshot(path=str(args.output / "final.png"), full_page=True, timeout=5000)
            except Exception as error:
                report["screenshot_error"] = str(error)
            await browser.close()

    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("IOS_WEBKIT_REPORT: " + json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))