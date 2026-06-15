from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
_INTERNAL_RULES = Path(__file__).resolve().parents[1] / "src/line1_core/rules/author_rules.yaml"
_PAPER_NAME = re.compile(r"\b[A-Z][A-Za-z]+\d{4}[a-z]?\b|\b[A-Z]{2,}\d{4}_[a-z0-9_]+\b")
_ALLOWED = {"CC0", "CC", "BY", "BSD", "DCAS", "SSDE", "TIER", "JETS"}


def _load_build_public():
    spec = importlib.util.spec_from_file_location("build_public", _TOOLS / "build_public.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _paper_names(text: str) -> set[str]:
    return {m.group(0) for m in _PAPER_NAME.finditer(text)} - _ALLOWED


def test_internal_rules_have_provenance() -> None:
    internal = yaml.safe_load(_INTERNAL_RULES.read_text(encoding="utf-8"))
    assert any(r.get("source_lessons") for r in internal["rules"]), "internal rules must keep source_lessons"


def test_public_build_strips_all_paper_names() -> None:
    bp = _load_build_public()
    internal = yaml.safe_load(_INTERNAL_RULES.read_text(encoding="utf-8"))
    public = bp._scrub_rules(internal)
    public_text = yaml.safe_dump(public, allow_unicode=True)
    leaks = _paper_names(public_text)
    assert not leaks, f"public rule set leaked paper names: {leaks}"
    assert "source_lessons" not in public_text


def test_public_preserves_rule_bodies() -> None:
    bp = _load_build_public()
    internal = yaml.safe_load(_INTERNAL_RULES.read_text(encoding="utf-8"))
    public = bp._scrub_rules(internal)
    assert len(public["rules"]) == len(internal["rules"])
    for pub_rule in public["rules"]:
        for field in ("id", "rule", "detection", "priority", "kind"):
            assert field in pub_rule


def test_leak_guard_catches_injected_paper_name() -> None:
    bp = _load_build_public()
    hits = bp._has_paper_name("Author should X (see Charron2013).")
    assert "Charron2013" in hits, "leak guard failed to catch an injected paper name"
