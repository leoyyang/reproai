from __future__ import annotations

from typing import Any

import re
from dataclasses import dataclass
from pathlib import Path

from .inventory import FileEntry

_STATA_DO = re.compile(r'^\s*(?:do|run)\s+"?([^",\r\n]+?\.do)"?', re.IGNORECASE | re.MULTILINE)
_STATA_USE = re.compile(r'^\s*use\s+"?([^",\r\n]+?\.dta)"?', re.IGNORECASE | re.MULTILINE)
_R_SOURCE = re.compile(r'source\(\s*["\']([^"\']+?\.[Rr])["\']', re.MULTILINE)
_PY_IMPORT_LOCAL = re.compile(r'^\s*(?:from|import)\s+([A-Za-z_][\w.]*)', re.MULTILINE)


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str
    resolved: bool


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _resolve(root: Path, from_rel: str, target: str) -> tuple[str, bool]:
    target_clean = target.strip().replace("\\", "/")
    base = Path(target_clean).name
    candidate = (root / from_rel).parent / Path(target_clean).name
    if candidate.exists():
        return str(candidate.relative_to(root)), True
    for path in root.rglob(base):
        if path.is_file():
            return str(path.relative_to(root)), True
    return target_clean, False


def build(root: Path, entries: list[FileEntry]) -> list[Edge]:
    root = root.resolve()
    edges: list[Edge] = []
    for entry in entries:
        if entry.language not in {"stata", "r", "python"}:
            continue
        text = _read_text(root, entry.path)
        patterns = []
        if entry.language == "stata":
            patterns = [(_STATA_DO, "do"), (_STATA_USE, "data_use")]
        elif entry.language == "r":
            patterns = [(_R_SOURCE, "source")]
        for regex, kind in patterns:
            for match in regex.finditer(text):
                dst, resolved = _resolve(root, entry.path, match.group(1))
                edges.append(Edge(src=entry.path, dst=dst, kind=kind, resolved=resolved))
    return edges


def entry_points(entries: list[FileEntry], edges: list[Edge]) -> list[dict[str, Any]]:
    code = {e.path for e in entries if e.language in {"stata", "r", "python"}}
    callers = {e.src for e in edges if e.kind in {"do", "source"}}
    called = {e.dst for e in edges if e.kind in {"do", "source"} and e.resolved}
    points: list[dict[str, Any]] = []
    for path in sorted(callers - called):
        points.append({"path": path, "reason": "runs other scripts but is not run by any"})
    if not callers:
        for path in sorted(code):
            name = Path(path).name.lower()
            if any(token in name for token in ("master", "main", "run_all", "runall", "00_", "_00")):
                points.append({"path": path, "reason": "name suggests a master/entry script"})
    return points
