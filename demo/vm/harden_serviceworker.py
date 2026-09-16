#!/usr/bin/env python3
"""Inject RESIDUAL's narrowly scoped immutable-disk retry into built WebVM.

The upstream service worker remains authoritative for cross-origin-isolation
headers. This hardening only retries same-origin hashed ext2 chunk GETs after a
network exception or HTTP 5xx, preventing a transient Pages/CDN failure from
immediately killing the browser VM.
"""
from __future__ import annotations

import sys
from pathlib import Path


def require_once(text: str, needle: str, label: str) -> None:
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"{label} moved: expected 1 occurrence, found {count}")


def harden(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "residualFetchWithRetry" in text:
        raise SystemExit("RESIDUAL disk retry already present; refusing duplicate injection")
    marker = "async function handleFetch(request) {"
    fetch_anchor = "\t\tvar r = await fetch(request);"
    require_once(text, marker, "WebVM handleFetch anchor")
    require_once(text, fetch_anchor, "WebVM fetch anchor")
    fragment = Path(__file__).with_name("serviceworker_retry_fragment.js").read_text(encoding="utf-8").rstrip()
    text = text.replace(marker, fragment + "\n\n" + marker, 1)
    text = text.replace(fetch_anchor, "\t\tvar r = await residualFetchWithRetry(request);", 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: harden_serviceworker.py PATH")
    harden(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
