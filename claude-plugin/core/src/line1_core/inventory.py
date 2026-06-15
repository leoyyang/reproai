from __future__ import annotations

from typing import Any

import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path

_LANG_BY_SUFFIX = {
    ".do": "stata",
    ".ado": "stata",
    ".r": "r",
    ".rmd": "r",
    ".py": "python",
    ".ipynb": "python",
    ".dta": "data",
    ".csv": "data",
    ".tab": "data",
    ".rds": "data",
    ".rdata": "data",
    ".xlsx": "data",
    ".parquet": "data",
    ".pdf": "doc",
    ".md": "doc",
    ".txt": "doc",
    ".tex": "doc",
}

_SKIP_DIRS = {".git", ".github", "__pycache__", ".ipynb_checkpoints", "renv", ".Rproj.user"}


@dataclass(frozen=True)
class FileEntry:
    path: str
    language: str
    size_bytes: int
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _language_of(path: Path) -> str:
    return _LANG_BY_SUFFIX.get(path.suffix.lower(), "other")


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(root: Path) -> list[FileEntry]:
    root = root.resolve()
    entries: list[FileEntry] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        entries.append(
            FileEntry(
                path=str(path.relative_to(root)),
                language=_language_of(path),
                size_bytes=path.stat().st_size,
                sha256=_sha256_of(path),
            )
        )
    return entries


def code_entries(entries: list[FileEntry]) -> list[FileEntry]:
    return [e for e in entries if e.language in {"stata", "r", "python"}]
