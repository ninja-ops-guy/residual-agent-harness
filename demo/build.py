"""Build only the explicitly public demo assets; no runtime data is published."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil

ASSETS = ("index.html", "styles.css", "app.mjs", "model.mjs", "favicon.svg", ".nojekyll")
SOURCE = Path(__file__).resolve().parent / "site"


def build(output: Path, revision: str = "local-unversioned", source: Path = SOURCE) -> Path:
    if not re.fullmatch(r"(?:[0-9a-f]{40}|local-unversioned)", revision):
        raise ValueError("Revision must be an exact lowercase Git commit SHA or local-unversioned")
    source = source.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Output must not already exist; choose a new empty destination")
    if output.resolve().is_relative_to(source):
        raise ValueError("Output cannot be inside the source asset directory")
    for name in ASSETS:
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Asset must be a regular file: {name}")
    html = (source / "index.html").read_text(encoding="utf-8")
    if html.count("__SOURCE_REVISION__") != 2:
        raise ValueError("Expected exactly two source-revision placeholders")
    output.mkdir(parents=True)
    for name in ASSETS:
        shutil.copyfile(source / name, output / name)
    (output / "index.html").write_text(html.replace("__SOURCE_REVISION__", revision), encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", default="local-unversioned")
    args = parser.parse_args()
    try:
        result = build(args.output, args.revision)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Demo build refused: {exc}\n")
    print(f"Built {len(ASSETS)} public assets at {result}; source={args.revision}; simulation=true")
