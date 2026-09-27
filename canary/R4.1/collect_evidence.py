#!/usr/bin/env python3
import argparse, pathlib
from canary_lib import sha256
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("evidence"); a=ap.parse_args(); root=pathlib.Path(a.evidence).resolve()
    lines=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file() and x.name!="SHA256SUMS"):
        lines.append(f"{sha256(p)}  {p.relative_to(root).as_posix()}")
    (root/"SHA256SUMS").write_text("\n".join(lines)+"\n",encoding="utf-8"); print(f"hashed {len(lines)} evidence files")
if __name__=="__main__": main()
