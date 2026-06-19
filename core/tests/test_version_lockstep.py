from __future__ import annotations

import json
import re
from pathlib import Path

# repo root: this file is at <root>/core/tests/test_version_lockstep.py
ROOT = Path(__file__).resolve().parents[2]


def _json_version(p: Path) -> str:
    return json.loads(p.read_text(encoding="utf-8"))["version"]


def _marketplace_version(p: Path) -> str:
    return json.loads(p.read_text(encoding="utf-8"))["metadata"]["version"]


def _re_version(p: Path, pattern: str) -> str:
    m = re.search(pattern, p.read_text(encoding="utf-8"), re.MULTILINE)
    assert m, f"no version match in {p}"
    return m.group(1)


def test_all_version_files_in_lockstep() -> None:
    # tools/bump_version.py must move every one of these together; this guards against the drift
    # that crept in when a manual edit touched the manifests but not pyproject/__init__.
    versions = {
        "claude plugin.json": _json_version(ROOT / "claude-plugin/.claude-plugin/plugin.json"),
        "codex plugin.json": _json_version(ROOT / "codex-plugin/.codex-plugin/plugin.json"),
        "marketplace.json": _marketplace_version(ROOT / "marketplace.json"),
        "pyproject.toml": _re_version(ROOT / "core/pyproject.toml", r'^version = "([^"]+)"'),
        "__init__.py": _re_version(ROOT / "core/src/line1_core/__init__.py", r'^__version__ = "([^"]+)"'),
    }
    assert len(set(versions.values())) == 1, f"version drift across files: {versions}"
