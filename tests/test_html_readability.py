"""Readability of the HTML report: flattened wrapper groups, no stray ':' prefix,
severity color accents."""

from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.reports.html import generate_html_fragment


def _rule_with_wrapper() -> ValidationResultGroup:
    """A rule group → internal '…Assertion' wrapper (no rule_reference) → leaf,
    mirroring what BaseAssertion.evaluate produces."""
    leaf = ValidationResult(
        valid=False,
        reference="",  # leaves carry no reference; the rule group does
        severity=Severity.ERROR,
        message="Data_type must follow format: ABBREV>Full_description",
        target="Data_type",
    )
    wrapper = ValidationResultGroup(
        name="MatchesAssertion",
        rule_reference="",
        severity=Severity.ERROR,
        results=[leaf],
    )
    rule = ValidationResultGroup(
        name="DataTypeFormat",
        rule_reference="ISTP-GA-006",
        severity=Severity.ERROR,
        results=[wrapper],
    )
    return ValidationResultGroup(
        name="AstraLint Results",
        rule_reference="",
        severity=Severity.INFO,
        results=[rule],
    )


def test_internal_assertion_wrapper_is_flattened():
    html = generate_html_fragment(_rule_with_wrapper())
    assert "MatchesAssertion" not in html, "internal wrapper layer should be flattened away"
    assert "DataTypeFormat" in html
    assert "ISTP-GA-006" in html


def test_no_stray_colon_prefix_for_empty_reference():
    html = generate_html_fragment(_rule_with_wrapper())
    # The leaf has no reference, so its message must not be prefixed with ": ".
    assert "</span>: <span" not in html.replace("\n", "")
    assert "Data_type must follow format" in html


def test_failed_results_get_a_severity_accent_class():
    html = generate_html_fragment(_rule_with_wrapper())
    assert "sev-ERROR" in html


def _rule_with_leaf(message: str, value: str) -> ValidationResultGroup:
    leaf = ValidationResult(
        valid=False, reference="", severity=Severity.ERROR, message=message, value=value
    )
    rule = ValidationResultGroup(
        name="R", rule_reference="ISTP-X", severity=Severity.ERROR, results=[leaf]
    )
    return ValidationResultGroup(
        name="root", rule_reference="", severity=Severity.INFO, results=[rule]
    )


def test_value_chip_shown_when_not_in_message():
    html = generate_html_fragment(
        _rule_with_leaf("Logical_file_id should follow the convention", "mms1_bad_name_v01")
    )
    assert 'class="value"' in html
    assert "mms1_bad_name_v01" in html


def test_value_chip_hidden_when_value_already_in_message():
    html = generate_html_fragment(_rule_with_leaf("has value 'foo', expected bar", "foo"))
    assert 'class="value"' not in html


def test_scalar_value_is_surfaced_on_assertion_results():
    """The base assertion attaches the checked scalar value to its results."""
    import re

    from astralint.base.file import Attribute, DataType, File
    from astralint.base.yaml_rules.assertions.matches import MatchesAssertion

    f = File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={
            "Logical_file_id": Attribute(
                name="Logical_file_id", data_type=[DataType.CHAR], shape=[1], values=["BAD VALUE"]
            )
        },
        variables={},
    )
    rule = MatchesAssertion(
        path="attributes/Logical_file_id/values/0", pattern=re.compile("^[a-z]+$"), message="bad"
    )
    result = rule.evaluate(f, Severity.ERROR)
    assert isinstance(result, ValidationResultGroup)
    leaf = result.results[0]
    assert isinstance(leaf, ValidationResult)
    assert leaf.value == "BAD VALUE"
