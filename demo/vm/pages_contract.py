#!/usr/bin/env python3
"""Publication-only checks. These are not guest/runtime verification."""
from __future__ import annotations

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path


IOS_PREFLIGHT_MARKER = "data-residual-ios-webkit-preflight"
IOS_PREFLIGHT_OPEN = f"<script {IOS_PREFLIGHT_MARKER}>"
IOS_PREFLIGHT_REQUIRED = (
    'params.get("full_vm") === "1"',
    "iPhone|iPad|iPod",
    'platform === "MacIntel"',
    "maxTouchPoints > 1",
    'new URL("../walkthrough/", location.href)',
    'target.searchParams.set("platform", "ios-webkit")',
    "location.replace(target.href)",
)


class EntryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refresh = False
        self.eager_optional = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta" and (values.get("http-equiv") or "").lower() == "refresh":
            self.refresh = True
        if tag == "script" and any(host in (values.get("src") or "") for host in ("js.puter.com", "plausible.leaningtech.com")):
            self.eager_optional = True


def validate_pages_config(config: dict) -> None:
    if config.get("build_type") != "workflow":
        raise ValueError("Pages source must be GitHub Actions, not Deploy from a branch. Change repository Settings > Pages > Build and deployment > Source > GitHub Actions.")


def _without_ios_preflight(html: str) -> str:
    if html.count(IOS_PREFLIGHT_OPEN) > 1:
        raise ValueError("Generated WebVM entry contains multiple iOS WebKit preflight scripts.")
    start = html.find(IOS_PREFLIGHT_OPEN)
    if start < 0:
        return html
    end = html.find("</script>", start)
    if end < 0:
        raise ValueError("The iOS WebKit preflight script is malformed.")
    script = html[start:end + len("</script>")]
    if any(required not in script for required in IOS_PREFLIGHT_REQUIRED):
        raise ValueError("The iOS WebKit preflight script is not the bounded walkthrough gate.")
    return html[:start] + html[end + len("</script>"):]


def validate_entry_html(html: str) -> None:
    entry = EntryParser()
    entry.feed(html)
    redirect_scope = _without_ios_preflight(html)
    if entry.refresh or "location.replace(" in redirect_scope or "location.assign(" in redirect_scope:
        raise ValueError("The WebVM entry is a redirect, not a generated VM application.")
    if entry.eager_optional:
        raise ValueError("Optional cloud/analytics script is eagerly loaded.")
    if "_app/immutable/entry/" not in html:
        raise ValueError("Generated WebVM JavaScript entry is missing.")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-config", type=Path)
    parser.add_argument("--demo-dir", type=Path)
    parser.add_argument("--commit")
    parser.add_argument("--webvm-commit")
    parser.add_argument("--disk", type=Path)
    args = parser.parse_args()
    if args.pages_config:
        validate_pages_config(json.loads(args.pages_config.read_text()))
        print("Pages publishing source: workflow")
    if args.demo_dir:
        index = args.demo_dir / "index.html"
        html = index.read_text()
        validate_entry_html(html)
        if IOS_PREFLIGHT_MARKER not in html:
            raise ValueError("Generated WebVM entry is missing the iOS WebKit preflight gate.")
        if args.commit:
            if not args.webvm_commit or not args.disk:
                parser.error("identity requires --webvm-commit and --disk")
            identity = {"commit": args.commit, "webvm_commit": args.webvm_commit,
                        "disk_sha256": sha256(args.disk),
                        "files": {name: sha256(args.demo_dir / name) for name in ("index.html", "serviceWorker.js")}}
            (args.demo_dir / "build-info.json").write_text(json.dumps(identity, indent=2) + "\n")
        print("Generated WebVM entry: validated (guest not yet tested)")
    if not args.pages_config and not args.demo_dir:
        parser.error("select --pages-config or --demo-dir")


if __name__ == "__main__":
    main()