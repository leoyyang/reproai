from __future__ import annotations

from line1_core import contribute

GOOD = """
schema_version: 1
venue: testj
profile_version: "2026-06-19"
checks:
  - check_id: TESTJ-README
    requirement: "A README at root."
    detector: readme_at_root
    source: "https://example.org/policy"
"""

GAP_OK = (
    "  - check_id: T-GAP\n"
    "    requirement: A codebook for every variable.\n"
    "    detector: unbuilt_detector\n"
    "    needs_detector: codebook_at_root\n"
    "    source: https://example.org/policy\n"
)
GAP_NO_TARGET = (
    "  - check_id: T-GAP\n"
    "    requirement: A codebook for every variable.\n"
    "    detector: unbuilt_detector\n"
    "    source: https://example.org/policy\n"
)


def test_validate_accepts_well_formed_draft() -> None:
    r = contribute.validate_venue_draft(GOOD)
    assert r["ok"], r["errors"]
    assert r["venue_id"] == "testj"
    assert r["dry_run"]["checks"] == 1


def test_validate_rejects_unknown_detector() -> None:
    r = contribute.validate_venue_draft(GOOD.replace("readme_at_root", "checks_the_codebook"))
    assert not r["ok"]
    assert any("unknown detector" in e for e in r["errors"])


def test_validate_rejects_unbuilt_without_target() -> None:
    r = contribute.validate_venue_draft(GOOD + GAP_NO_TARGET)
    assert not r["ok"]
    assert any("needs_detector" in e for e in r["errors"])


def test_validate_accepts_unbuilt_with_target() -> None:
    r = contribute.validate_venue_draft(GOOD + GAP_OK)
    assert r["ok"], r["errors"]


def test_validate_rejects_bad_venue_id() -> None:
    r = contribute.validate_venue_draft(GOOD.replace("venue: testj", "venue: Test J"))
    assert not r["ok"]
    assert any("venue id" in e for e in r["errors"])


def test_validate_rejects_non_mapping() -> None:
    r = contribute.validate_venue_draft("- a\n- b\n")
    assert not r["ok"]


def test_scrub_flags_identifiers() -> None:
    leaks = contribute.scrub_leaks("path /Users/jane/x.tex email a@b.edu orcid 0000-0002-1825-0097")
    labels = {lk["label"] for lk in leaks}
    assert {"absolute home path", "email address", "ORCID"} <= labels


def test_scrub_passes_clean_text() -> None:
    assert contribute.scrub_leaks("relative path data/x.csv, run master.R, no identifiers") == []
