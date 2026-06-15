from __future__ import annotations

from typing import Any

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .inventory import FileEntry

_VENUE_DIR = Path(__file__).parent / "venues"

_README_SECTION_HINTS = [
    "data availability",
    "computational requirement",
    "instructions",
    "data source",
]
_ABS_PATH = re.compile(r'(?:[A-Za-z]:\\|\\\\|/Users/|/home/|~/)')


@dataclass
class Check:
    check_id: str
    requirement: str
    status: str
    detail: str
    evidence: list[str]
    source: str


def load_profile(venue: str) -> dict[str, Any]:
    path = _VENUE_DIR / f"{venue}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No venue profile for '{venue}' at {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _root_readme(root: Path) -> Path | None:
    for name in ("README.pdf", "Readme.pdf", "readme.pdf"):
        if (root / name).exists():
            return root / name
    return None


def _has_master(entries: list[FileEntry]) -> bool:
    for e in entries:
        name = Path(e.path).name.lower()
        if e.language in {"stata", "r", "python"} and any(
            t in name for t in ("master", "main", "run_all", "runall")
        ):
            return True
    return False


def _file_count(entries: list[FileEntry]) -> int:
    return len(entries)


def _any_abs_path(root: Path, entries: list[FileEntry]) -> bool:
    for e in entries:
        if e.language in {"stata", "r", "python"}:
            try:
                if _ABS_PATH.search((root / e.path).read_text(encoding="utf-8", errors="replace")):
                    return True
            except OSError:
                continue
    return False


def _env_declared(root: Path, entries: list[FileEntry]) -> bool:
    readme = _root_readme(root)
    if readme is None:
        for e in entries:
            if Path(e.path).name.lower() in {"readme.md", "readme.txt"}:
                return True
        return False
    return True


def run(root: Path, entries: list[FileEntry], venue: str) -> tuple[dict[str, Any], list[Check]]:
    root = root.resolve()
    profile = load_profile(venue)
    checks: list[Check] = []

    def add(spec: dict[str, Any], status: str, detail: str, evidence: list[str]) -> None:
        checks.append(
            Check(
                check_id=spec["check_id"],
                requirement=spec["requirement"],
                status=status,
                detail=detail,
                evidence=evidence,
                source=spec.get("source", ""),
            )
        )

    for spec in profile.get("checks", []):
        detector = spec.get("detector")
        if detector == "readme_pdf_at_root":
            readme = _root_readme(root)
            add(spec, "pass" if readme else "fail",
                "README.pdf at root" if readme else "No README.pdf in the uppermost directory.",
                [readme.name] if readme else [])
        elif detector == "readme_has_sections":
            readme = _root_readme(root)
            md = next((e.path for e in entries if Path(e.path).name.lower() in {"readme.md", "readme.txt"}), None)
            if readme is None and md is None:
                add(spec, "fail", "No README found to check sections.", [])
            elif md is not None:
                text = (root / md).read_text(encoding="utf-8", errors="replace").lower()
                missing = [h for h in _README_SECTION_HINTS if h not in text]
                add(spec, "pass" if not missing else "needs_author_action",
                    "All key sections present." if not missing else f"Missing sections: {', '.join(missing)}.",
                    [md])
            else:
                evidence = [readme.name] if readme is not None else []
                add(spec, "needs_author_action", "README.pdf present; section content not statically inspectable.", evidence)
        elif detector == "has_master_script":
            ok = _has_master(entries)
            add(spec, "pass" if ok else "needs_author_action",
                "Master script detected." if ok else "No master/run-all script found.", [])
        elif detector == "env_declared":
            ok = _env_declared(root, entries)
            add(spec, "pass" if ok else "needs_author_action",
                "README present to carry environment statement." if ok else "No README to declare software/versions.", [])
        elif detector == "no_absolute_paths":
            bad = _any_abs_path(root, entries)
            add(spec, "fail" if bad else "pass",
                "Absolute paths present (exceeds single-path-edit tolerance)." if bad else "No absolute paths detected.", [])
        elif detector == "rederive_from_raw":
            add(spec, "needs_author_action", "Static check cannot confirm raw-to-analysis re-derivation; author must confirm.", [])
        elif detector == "file_count_limit":
            n = _file_count(entries)
            limit = profile.get("deposit", {}).get("max_files")
            if limit is None:
                add(spec, "needs_author_action", f"{n} files; this venue sets no explicit file-count limit but keep the deposit navigable.", [])
            else:
                add(spec, "pass" if n <= limit else "needs_author_action",
                    f"{n} files (limit {limit}; zip if exceeded).", [])
        elif detector == "manual_author_action":
            add(spec, "needs_author_action", "Requires an author action that cannot be verified statically.", [])
        else:
            add(spec, "not_applicable", f"Unknown detector '{detector}'.", [])

    summary = {
        "total": len(checks),
        "pass": sum(1 for c in checks if c.status == "pass"),
        "fail": sum(1 for c in checks if c.status == "fail"),
        "needs_author_action": sum(1 for c in checks if c.status == "needs_author_action"),
    }
    meta = {
        "venue": profile["venue"],
        "profile_version": profile["profile_version"],
        "standard": profile.get("standard", ""),
        "summary": summary,
    }
    return meta, checks
