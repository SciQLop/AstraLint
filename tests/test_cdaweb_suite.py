"""CDAWeb conformance suite: inherits ISTP and tightens CDAWeb-required rules."""

from pathlib import Path

import pytest

import astralint
from astralint.base.conformance_suite import (
    ConformanceSuite,
    _ConformanceSuiteProtocolCtor,
    get_suite,
)
from astralint.base.file import Attribute, DataType, File
from astralint.base.validation_result import ValidationResultGroup
from astralint.base.yaml_rules.yaml_rule import load_yaml_rule

SUITES_DIR = Path(astralint.__file__).parent / "suites"


def suite(name: str) -> ConformanceSuite:
    s = get_suite(name)
    assert s is not None, f"suite {name} should be registered"
    return s


def attr(name: str, values: list) -> Attribute:
    return Attribute(name=name, data_type=[DataType.CHAR], shape=[len(values)], values=values)


def make_file(global_attrs: dict) -> File:
    return File(
        extension="cdf",
        filename="test.cdf",
        compression="NONE",
        attributes=global_attrs,
        variables={},
    )


def _severity(suite_name: str, reference: str) -> str:
    return next(r.severity.value for r in suite(suite_name).rules if r.reference == reference)


def test_cdaweb_inherits_all_istp_rules_and_adds_its_own():
    istp_refs = {r.reference for r in suite("ISTP").rules}
    cdaweb_refs = {r.reference for r in suite("CDAWeb").rules}
    assert istp_refs <= cdaweb_refs, "CDAWeb must inherit every ISTP rule"
    assert "CDAWEB-GA-001" in cdaweb_refs, "CDAWeb must add its own entry-limit rule"


def test_cdaweb_promotes_required_attrs_to_error():
    assert _severity("ISTP", "ISTP-GA-016") == "WARNING"
    assert _severity("CDAWeb", "ISTP-GA-016") == "ERROR"


def test_severity_override_changes_finding_severity():
    """A file missing Instrument_type/Mission_group is a warning under ISTP but an
    error under the CDAWeb profile."""
    f = make_file({})

    def has(suite_name: str, sev: str) -> bool:
        rule = next(r for r in suite(suite_name).rules if r.reference == "ISTP-GA-016")
        result = rule.check(f)
        assert isinstance(result, ValidationResultGroup)
        return result.count_by_severity()[sev] > 0

    assert has("ISTP", "WARNING")
    assert has("CDAWeb", "ERROR")


def test_cdaweb_entry_limit_flags_more_than_five():
    rule = load_yaml_rule(SUITES_DIR / "CDAWeb" / "rules" / "CDAWebEntryLimits.yaml")
    too_many = make_file({"Instrument_type": attr("Instrument_type", ["Particles (space)"] * 6)})
    assert not rule.check(too_many).valid
    ok = make_file({"Instrument_type": attr("Instrument_type", ["Particles (space)"] * 5)})
    assert rule.check(ok).valid


def test_suite_construction_is_idempotent():
    """Regression: loading a suite twice must not duplicate its rules."""
    first = len(suite("ISTP").rules)
    second = len(suite("ISTP").rules)
    assert first == second


def test_invalid_severity_override_raises_contextual_error():
    ctor = _ConformanceSuiteProtocolCtor(
        name="BadSuite",
        rules_lookup_dir="/nonexistent",
        severity_overrides={"ISTP-GA-016": "CRITICAL"},
        description="x",
        url="x",
    )
    with pytest.raises(ValueError, match="BadSuite"):
        ctor()
