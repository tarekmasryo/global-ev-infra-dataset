from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_checksums(root: Path, out_file: Path, include_patterns: list[str]) -> None:
    paths: list[Path] = []
    for pat in include_patterns:
        paths.extend(root.glob(pat))
    # unique + stable order
    uniq = sorted({p.resolve() for p in paths if p.is_file()})
    lines = []
    for p in uniq:
        rel = p.relative_to(root)
        lines.append(f"{sha256_file(p)}  {rel.as_posix()}")
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Wrote {out_file.as_posix()} ({len(lines)} entries)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Write SHA256 checksums for dataset files.")
    p.add_argument("--root", type=Path, default=Path("."), help="Repo root.")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("checksums.sha256"),
        help="Output checksums file.",
    )
    p.add_argument(
        "--include",
        nargs="+",
        default=[
            "data/*.csv",
            "README.md",
            "CHANGELOG.md",
            "data_dictionary.csv",
            "OCM_CC_BY_4.0.txt",
        ],
        help="Glob patterns (relative to root).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    write_checksums(args.root.resolve(), args.root.resolve() / args.out, args.include)


if __name__ == "__main__":
    main()
