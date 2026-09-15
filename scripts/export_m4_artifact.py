#!/usr/bin/env python3
"""Export the uploaded M4 ZIP through retained CI logs, verifying its digest.

This read-only transport supplements the normal Actions artifact when the
consumer cannot retrieve its signed download URL. It does not qualify results.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse
import zipfile

MAX_ARCHIVE_BYTES = 1024 * 1024
FILES = {"dependencies.txt", "source-environment.json", "report.json",
         "probe.log", "tests.log", "m4-sandbox.xml"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main() -> None:
    artifact = int(os.environ["M4_ARTIFACT_ID"])
    expected = os.environ["M4_ARTIFACT_DIGEST"].removeprefix("sha256:")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"]
        + f"/actions/artifacts/{artifact}/zip",
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            data = response.read(MAX_ARCHIVE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code != 302:
            raise RuntimeError(f"Artifact API returned HTTP {exc.code}") from None
        location = exc.headers["Location"]
        if urlparse(location).scheme != "https":
            raise RuntimeError("Artifact redirect must use HTTPS")
        # Never forward the repository token to the storage redirect.
        with urllib.request.urlopen(location, timeout=30) as response:
            data = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise RuntimeError("M4 archive exceeds export size bound")
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected:
        raise RuntimeError("Downloaded archive does not match upload digest")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if not set(archive.namelist()) <= FILES:
            raise RuntimeError("Unexpected files in M4 artifact")
    print("M4_ARCHIVE_BEGIN " + json.dumps({"artifact_id": artifact,
          "sha256": digest, "size": len(data)}, sort_keys=True))
    encoded = base64.b64encode(data).decode("ascii")
    for offset in range(0, len(encoded), 3072):
        print("M4_ARCHIVE_DATA " + encoded[offset:offset + 3072])
    print("M4_ARCHIVE_END")


if __name__ == "__main__":
    main()
