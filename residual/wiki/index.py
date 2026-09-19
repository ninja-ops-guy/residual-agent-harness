"""Deterministic, local index over the repository documentation tree."""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from residual.core import ContractError, digest

_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".json", ".toml", ".yaml", ".yml"}
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+/-]{1,63}")
_HEADING_RE = re.compile(r"^#{1,6}\\s+(.+?)\\s*$", re.MULTILINE)
_MAX_DOC_BYTES = 512 * 1024
_MAX_TOTAL_BYTES = 24 * 1024 * 1024
_MAX_DOCS = 2000


def resolve_docs_root(explicit: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env = os.environ.get("RESIDUAL_DOCS_ROOT")
    if env:
        candidates.append(Path(env))
    candidates.append(Path(__file__).resolve().parents[2] / "docs")
    candidates.append(Path.cwd() / "docs")
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_dir():
            return resolved
    raise ContractError(
        "RESIDUAL documentation directory was not found; set RESIDUAL_DOCS_ROOT"
    )


def _clean_title(value: str) -> str:
    text = value.replace(chr(96), "")
    text = re.sub(r"[*_#]+", "", text).strip()
    return text[:180] or "Untitled"


def _summary(text: str) -> str:
    lines: list[str] = []
    fenced = False
    fence = chr(96) * 3
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(fence):
            fenced = not fenced
            continue
        if fenced or not line or line.startswith("#"):
            if lines:
                break
            continue
        if line.startswith(("|", "- ", "* ", ">")) and not lines:
            continue
        lines.append(re.sub(r"\\s+", " ", line))
        if len(" ".join(lines)) >= 360:
            break
    return " ".join(lines)[:420]


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(m.group(0).lower() for m in _TOKEN_RE.finditer(value)))


@dataclass(frozen=True)
class WikiDocument:
    path: str
    title: str
    category: str
    summary: str
    headings: tuple[str, ...]
    content: str
    sha256: str
    size: int

    def public(self, *, include_content: bool = False) -> dict:
        value = {
            "path": self.path,
            "title": self.title,
            "category": self.category,
            "summary": self.summary,
            "headings": list(self.headings),
            "sha256": self.sha256,
            "size": self.size,
        }
        if include_content:
            value["content"] = self.content
        return value


@dataclass(frozen=True)
class WikiSearchHit:
    path: str
    title: str
    category: str
    excerpt: str
    score: int
    sha256: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "title": self.title,
            "category": self.category,
            "excerpt": self.excerpt,
            "score": self.score,
            "sha256": self.sha256,
        }


class WikiIndex:
    """Read-only index. Symlinks and out-of-root paths are never indexed."""

    def __init__(self, root: str | Path | None = None):
        self.root = resolve_docs_root(root)
        self._documents = self._build()
        self._by_path = {doc.path: doc for doc in self._documents}
        self._categories: dict[str, int] = {}
        for doc in self._documents:
            self._categories[doc.category] = self._categories.get(doc.category, 0) + 1

    def _build(self) -> tuple[WikiDocument, ...]:
        docs: list[WikiDocument] = []
        total = 0
        root = self.root
        for path in sorted(root.rglob("*")):
            if len(docs) >= _MAX_DOCS:
                raise ContractError("documentation index exceeds file limit")
            if (
                not path.is_file()
                or path.is_symlink()
                or path.suffix.lower() not in _TEXT_SUFFIXES
            ):
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
            except (OSError, ValueError):
                continue
            size = path.stat().st_size
            if size <= 0 or size > _MAX_DOC_BYTES:
                continue
            total += size
            if total > _MAX_TOTAL_BYTES:
                raise ContractError("documentation index exceeds total byte limit")
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            rel = path.relative_to(root).as_posix()
            headings = tuple(_clean_title(x) for x in _HEADING_RE.findall(text)[:80])
            title = (
                headings[0]
                if headings
                else _clean_title(path.stem.replace("-", " ").replace("_", " "))
            )
            first = rel.split("/", 1)[0]
            category = first if "/" in rel else "root"
            docs.append(
                WikiDocument(
                    path=rel,
                    title=title,
                    category=category,
                    summary=_summary(text),
                    headings=headings,
                    content=text,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    size=len(raw),
                )
            )
        if not docs:
            raise ContractError("documentation index contains no readable documents")
        return tuple(docs)

    @property
    def documents(self) -> tuple[WikiDocument, ...]:
        return self._documents

    def summary(self) -> dict:
        return {
            "source": "docs/",
            "documents": len(self._documents),
            "bytes": sum(doc.size for doc in self._documents),
            "categories": [
                {"name": name, "documents": count}
                for name, count in sorted(self._categories.items())
            ],
            "index_hash": digest(
                [{"path": d.path, "sha256": d.sha256} for d in self._documents]
            ),
        }

    def list_documents(self, category: str | None = None) -> list[dict]:
        docs = self._documents
        if category:
            docs = tuple(doc for doc in docs if doc.category == category)
        return [doc.public() for doc in docs]

    def read(self, path: str) -> WikiDocument:
        if not isinstance(path, str) or not path or len(path) > 600:
            raise ContractError("invalid documentation path")
        doc = self._by_path.get(path)
        if doc is None:
            raise ContractError("documentation page not found")
        return doc

    def search(self, query: str, *, limit: int = 8) -> tuple[WikiSearchHit, ...]:
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise ContractError("wiki search query must be 1-500 characters")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ContractError("wiki search limit must be 1-20")
        terms = _tokens(query)
        if not terms:
            raise ContractError("wiki search query has no searchable terms")
        ranked: list[tuple[int, WikiDocument, int]] = []
        for doc in self._documents:
            title = doc.title.lower()
            path = doc.path.lower()
            headings = " ".join(doc.headings).lower()
            body = doc.content.lower()
            score = 0
            first_at = len(body)
            for term in terms:
                score += 18 * title.count(term)
                score += 10 * path.count(term)
                score += 8 * headings.count(term)
                score += min(body.count(term), 12)
                pos = body.find(term)
                if pos >= 0:
                    first_at = min(first_at, pos)
            if score:
                ranked.append((score, doc, first_at))
        ranked.sort(key=lambda row: (-row[0], row[1].path))
        hits = []
        for score, doc, pos in ranked[:limit]:
            start = max(0, pos - 180) if pos < len(doc.content) else 0
            end = min(len(doc.content), start + 520)
            excerpt = re.sub(r"\\s+", " ", doc.content[start:end]).strip()
            hits.append(
                WikiSearchHit(
                    doc.path,
                    doc.title,
                    doc.category,
                    excerpt,
                    score,
                    doc.sha256,
                )
            )
        return tuple(hits)
