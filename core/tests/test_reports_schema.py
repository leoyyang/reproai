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


@pytest.mark.parametrize("venue", ["aea", "apsr", "ajps", "jop", "generic_dataverse", "generic_openicpsr"])
def test_all_venue_profiles_run(messy_pkg: Path, venue: str) -> None:
    result = coordinator.check(messy_pkg, venue)
    vc = result["venue_compliance_report"]
    assert vc is not None
    assert vc["venue"] == venue
    assert vc["summary"]["total"] > 0


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
