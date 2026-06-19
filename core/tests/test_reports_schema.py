from __future__ import annotations

import json
from pathlib import Path

import pytest
from line1_core import coordinator

jsonschema = pytest.importorskip("jsonschema")

_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "src/line1_core/schemas"
_PAIRS = {
    "architecture_report": "architecture_report.schema.json",
    "advisory_plan": "advisory_plan.schema.json",
    "venue_compliance_report": "venue_compliance_report.schema.json",
    "risk_register": "risk_register.schema.json",
}


@pytest.mark.parametrize("key,schema_file", list(_PAIRS.items()))
def test_report_matches_schema(messy_pkg: Path, key: str, schema_file: str) -> None:
    result = coordinator.check(messy_pkg, "aea")
    schema = json.loads((_SCHEMA_DIR / schema_file).read_text(encoding="utf-8"))
    jsonschema.validate(instance=result[key], schema=schema)


# glob the shipped profiles so a newly added venues/<id>.yaml is matrix-tested automatically —
# no hand-edited parametrize list to forget (the gap the contribute flow would otherwise leave).
_VENUES_DIR = Path(__file__).resolve().parents[1] / "src" / "line1_core" / "venues"
_ALL_VENUES = sorted(p.stem for p in _VENUES_DIR.glob("*.yaml"))


@pytest.mark.parametrize("venue", _ALL_VENUES)
def test_all_venue_profiles_run(messy_pkg: Path, venue: str) -> None:
    result = coordinator.check(messy_pkg, venue)
    vc = result["venue_compliance_report"]
    assert vc is not None
    assert vc["venue"] == venue
    assert vc["summary"]["total"] > 0


def test_manual_action_detail_is_specific_not_a_stub() -> None:
    # the manual_author_action branch must carry the check's own author_action-or-requirement as the
    # detail, not the old generic "cannot be verified statically" stub.
    from line1_core import inventory, venue_engine

    root = Path(__file__).resolve().parents[1]
    entries = inventory.scan(root)
    seen = 0
    for venue in _ALL_VENUES:
        profile = venue_engine.load_profile(venue)
        by_id = {c["check_id"]: c for c in profile.get("checks", [])}
        _, checks = venue_engine.run_profile(root, entries, profile)
        for c in checks:
            spec = by_id.get(c.check_id, {})
            if spec.get("detector") == "manual_author_action":
                seen += 1
                expected = spec.get("author_action") or spec["requirement"]
                assert c.detail == expected
                assert "cannot be verified statically" not in c.detail
    assert seen > 0


def test_reclassified_checks_compute_real_status() -> None:
    # the 4 mis-tiered checks now run real static detectors: a computed status from the new detector
    # set, not the manual_author_action stub.
    from line1_core import inventory, venue_engine

    root = Path(__file__).resolve().parents[1]
    entries = inventory.scan(root)
    cases = {
        "worldbank": ("WB-DATA-AVAILABILITY", "data_availability_statement"),
        "apsr": ("APSR-DATA-AVAILABILITY", "data_availability_statement"),
        "generic_dataverse": ("GEN-DV-DATA-CITATION", "data_citation"),
        "jasa": ("JASA-REPRO-RNG", "seeded_rng"),
    }
    computed = {"pass", "fail", "needs_author_action"}
    for venue, (check_id, detector) in cases.items():
        profile = venue_engine.load_profile(venue)
        spec = next(c for c in profile["checks"] if c["check_id"] == check_id)
        assert spec["detector"] == detector
        _, checks = venue_engine.run_profile(root, entries, profile)
        c = next(x for x in checks if x.check_id == check_id)
        assert c.status in computed
        assert "Requires an author action that cannot be verified statically." not in c.detail


def test_no_unbuilt_detectors_in_shipped_profiles() -> None:
    # a profile that parks a gap on `unbuilt_detector` must build the real detector (or consciously
    # demote the check) before it ships — this keeps an owed detector from rotting invisibly.
    from line1_core import venue_engine

    offenders = []
    for venue in _ALL_VENUES:
        if venue.startswith("generic_"):
            continue
        for c in venue_engine.load_profile(venue).get("checks", []):
            if c.get("detector") == "unbuilt_detector":
                offenders.append(f"{venue}:{c.get('check_id')}")
    assert not offenders, f"shipped profiles still carry unbuilt_detector: {offenders}"


def test_every_finding_carries_a_rewrite_contract(messy_pkg: Path) -> None:
    adv = coordinator.check(messy_pkg, "aea")["advisory_plan"]
    assert adv["lossless_contract"], "lossless_contract must be present and non-empty"
    assert adv["items"], "fixture should produce findings"
    for it in adv["items"]:
        rw = it["rewrite"]
        assert rw["mode"] in {"llm_rewrite", "propose_only"}
        fp = rw["fix_prompt"]
        assert it["rule_id"] in fp and it["priority"] in fp
        assert "TARGET FORM:" in fp and "WHY IT HURTS DOWNSTREAM:" in fp


def test_propose_only_rules_never_marked_rewritable(messy_pkg: Path) -> None:
    adv = coordinator.check(messy_pkg, "aea")["advisory_plan"]
    semantic = {
        "A6-guarded-fallback-load", "A7-var-lifecycle-contradiction", "B10-embedded-foreign-code",
        "A1-master-entry", "C4-deprecated-syntax-signature", "C5-deprecated-r-packages",
        "N4-named-estimation-calls", "A4-panel-declare", "A10-commented-restricted-regression",
        "B3-no-wide-wildcard", "B6-rederive-from-raw",
    }
    for it in adv["items"]:
        if it["rule_id"] in semantic:
            assert it["rewrite"]["mode"] == "propose_only", (
                f"{it['rule_id']} is semantic and must never be llm_rewrite"
            )
