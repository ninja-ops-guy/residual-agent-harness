from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "sha256:605e8292d9d3e5288094fb9dffd68869a19771546cc11d7c3c777f9d7e0f705d"
IMAGE = "i386/debian:bookworm-slim"
FILES = (
    ROOT / "demo" / "vm" / "Dockerfile",
    ROOT / ".github" / "workflows" / "webvm-runtime-wait-primitive.yml",
    ROOT / ".github" / "workflows" / "webvm-runtime-clock-path.yml",
    ROOT / ".github" / "workflows" / "webvm-runtime-sleep-threshold.yml",
    ROOT / ".github" / "workflows" / "webvm-runtime-libc-sleep-wrapper.yml",
    ROOT / ".github" / "workflows" / "webvm-runtime-raw-sleep-syscall.yml",
)


class WebVMBaseImagePinTests(unittest.TestCase):
    def test_all_webvm_debian_refs_are_digest_pinned(self):
        seen = 0
        expected = IMAGE + "@" + EXPECTED
        mutable = re.compile(r"(?<![A-Za-z0-9_.-])" + re.escape(IMAGE) + r"(?!@sha256:[0-9a-f]{64})")
        for path in FILES:
            body = path.read_text(encoding="utf-8")
            self.assertNotRegex(body, mutable, f"{path} contains mutable WebVM base image ref")
            if expected in body:
                seen += body.count(expected)
        self.assertEqual(seen, len(FILES), "every governed WebVM build/control must use the reviewed digest")

    def test_dockerfile_keeps_linux_386_platform_binding(self):
        body = FILES[0].read_text(encoding="utf-8")
        self.assertIn(
            "FROM --platform=linux/386 docker.io/" + IMAGE + "@" + EXPECTED,
            body,
        )


if __name__ == "__main__":
    unittest.main()
