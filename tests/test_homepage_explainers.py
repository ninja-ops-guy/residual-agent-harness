from html.parser import HTMLParser
from pathlib import Path
import re


HOME = Path(__file__).parents[1] / "site" / "index.html"
EXPECTED = {
    "contract",
    "workers",
    "evidence",
    "verify",
    "residual",
    "integrate",
    "receipt",
    "claims",
    "verifier-quality",
    "authority",
    "implemented",
    "validation",
    "evaluation",
}


class HomepageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.explainers: dict[str, tuple[str, dict[str, str | None]]] = {}
        self.ids: set[str] = set()
        self.dialog_label: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.add(element_id)
        if key := attributes.get("data-explainer"):
            self.explainers[key] = (tag, attributes)
        if tag == "dialog" and attributes.get("id") == "detail-dialog":
            self.dialog_label = attributes.get("aria-labelledby")


def test_homepage_explainers_are_complete_and_keyboard_accessible() -> None:
    source = HOME.read_text(encoding="utf-8")
    parser = HomepageParser()
    parser.feed(source)

    assert set(parser.explainers) == EXPECTED
    for tag, attributes in parser.explainers.values():
        if tag == "button":
            assert attributes.get("type") == "button"
        else:
            assert attributes.get("role") == "button"
            assert attributes.get("tabindex") == "0"
            assert attributes.get("aria-haspopup") == "dialog"

    assert parser.dialog_label == "detail-title"
    assert parser.dialog_label in parser.ids
    assert {f"detail-{name}" for name in ("kicker", "title", "summary", "input", "output", "failure", "rule", "why")} <= parser.ids

    object_source = source.split("const explanations = {", 1)[1].split("const dialog =", 1)[0]
    declared = {
        quoted or plain
        for quoted, plain in re.findall(r'^\s+(?:"([^"]+)"|([\w-]+)):\s*\{$', object_source, re.MULTILINE)
    }
    assert declared == EXPECTED
    assert 'event.key === "Enter" || event.key === " "' in source
    assert "dialog.showModal()" in source
    assert 'dialog.addEventListener("close"' in source
