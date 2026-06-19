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
    # Case-insensitive: JASA's own template ships "ReadMe.pdf", which a case-sensitive
    # filesystem (Linux CI, where reproducibility checks run) would otherwise miss.
    try:
        for child in root.iterdir():
            if child.is_file() and child.name.lower() == "readme.pdf":
                return child
    except OSError:
        return None
    return None


def _license_at_root(root: Path) -> str | None:
    names = {"license", "license.md", "license.txt", "licence", "licence.md", "licence.txt", "copying"}
    try:
        for child in root.iterdir():
            if child.is_file() and child.name.lower() in names:
                return child.name
    except OSError:
        return None
    return None


def _pdftotext(path: Path) -> str | None:
    """Extract text from a PDF README via poppler's `pdftotext`, when available. Reading a document is
    not executing author code. Returns None on any failure (no poppler, extraction error) so the caller
    falls back gracefully — no hard dependency is introduced."""
    import shutil
    import subprocess

    exe = shutil.which("pdftotext")
    if exe is None:
        return None
    try:
        proc = subprocess.run([exe, "-q", str(path), "-"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


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
        elif detector == "readme_at_root":
            # softer than readme_pdf_at_root: any README at root passes; PDF is recommended, not required
            pdf = _root_readme(root)
            md = next((e.path for e in entries if Path(e.path).name.lower() in {"readme.md", "readme.txt"}), None)
            if pdf:
                add(spec, "pass", f"README present at root ({pdf.name}).", [pdf.name])
            elif md:
                add(spec, "needs_author_action", "README present, but the JASA template ships ReadMe.pdf; export a PDF copy.", [md])
            else:
                add(spec, "fail", "No README at the package root.", [])
        elif detector == "readme_has_sections":
            # a profile may override the section hints to match its own README template
            hints = profile.get("readme_sections") or _README_SECTION_HINTS
            readme = _root_readme(root)
            md = next((e.path for e in entries if Path(e.path).name.lower() in {"readme.md", "readme.txt"}), None)
            # prefer a plain-text README; otherwise read the PDF's text so its sections count too
            text = None
            src = None
            if md is not None:
                text = (root / md).read_text(encoding="utf-8", errors="replace").lower()
                src = md
            elif readme is not None:
                extracted = _pdftotext(readme)
                if extracted is not None:
                    text = extracted.lower()
                    src = readme.name
            if text is not None:
                missing = [h for h in hints if h not in text]
                add(spec, "pass" if not missing else "needs_author_action",
                    "All key sections present." if not missing else f"Missing sections: {', '.join(missing)}.",
                    [src])
            elif readme is not None:
                add(spec, "needs_author_action",
                    "README.pdf present but its text could not be extracted (install poppler's pdftotext to auto-check sections).",
                    [readme.name])
            else:
                add(spec, "fail", "No README found to check sections.", [])
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
        elif detector == "license_at_root":
            lic = _license_at_root(root)
            add(spec, "pass" if lic else "fail",
                f"License file present ({lic})." if lic else "No LICENSE file at the package root.",
                [lic] if lic else [])
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
