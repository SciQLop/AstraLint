import re
from typing import Any

import pytest

from astralint.base.file import Attribute, DataType, File, Variable
from astralint.base.validation_result import Severity, ValidationResult, ValidationResultGroup
from astralint.base.yaml_rules.assertions.base import clean_target, render_message
from astralint.base.yaml_rules.assertions.collections import (
    ContainsAssertion,
    LengthAssertion,
    NotContainsAssertion,
    NotEmptyAssertion,
    RequiresAssertion,
)
from astralint.base.yaml_rules.assertions.compare_to import CompareToAssertion
from astralint.base.yaml_rules.assertions.comparisons import (
    ComparisonAssertion,
    RangeAssertion,
)
from astralint.base.yaml_rules.assertions.contains_keys import ContainsKeysAssertion
from astralint.base.yaml_rules.assertions.exists import ExistsAssertion
from astralint.base.yaml_rules.assertions.is_type import IsTypeAssertion
from astralint.base.yaml_rules.assertions.matches import MatchesAssertion
from astralint.base.yaml_rules.assertions.relatioship import ReferencesVariableAssertion

from . import *  # isort:skip # noqa: F403


def _leaf(result: ValidationResult | ValidationResultGroup) -> ValidationResult:
    """Extract the first leaf ValidationResult from a result or group."""
    if isinstance(result, ValidationResult):
        return result
    return _leaf(result.results[0])


# =============================================================================
# clean_target tests
# =============================================================================


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        ("variables/B/attributes/CATDESC/values/0", "B/CATDESC"),
        ("variables/Epoch/attributes/UNITS/values/0", "Epoch/UNITS"),
        ("variables/B/data_type", "B"),
        ("attributes/Logical_source/values/0", "Logical_source"),
        ("attributes/DOI/values/0", "DOI"),
        ("attributes", ""),
        ("Global", ""),
        ("variables/.*/attributes/CATDESC/values/0", "CATDESC"),
    ],
)
def test_clean_target(raw_path: str, expected: str) -> None:
    assert clean_target(raw_path) == expected


# =============================================================================
# render_message tests
# =============================================================================


def test_render_message_simple() -> None:
    result = render_message("'{{ value }}' does not match", {"value": "hello"})
    assert result == "'hello' does not match"


def test_render_message_with_filter() -> None:
    result = render_message("{{ values | join(', ') }}", {"values": ["a", "b", "c"]})
    assert result == "a, b, c"


def test_render_message_with_none_default() -> None:
    result = render_message("{{ attribute or 'unknown' }} is empty", {"attribute": None})
    assert result == "unknown is empty"


def test_render_message_bad_template_does_not_crash() -> None:
    result = render_message("{% if broken %", {"valid": True})
    assert "[template error" in result


def test_render_message_with_attribute() -> None:
    result = render_message(
        "{{ attribute or path }} is empty", {"attribute": "CATDESC", "path": "x/y"}
    )
    assert result == "CATDESC is empty"


# =============================================================================
# BaseAssertion no-match tests
# =============================================================================


def test_base_assertion_no_match_message(mock_file: Any) -> None:
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/NonExistent/values/0",
        operator="=",
        value=42,
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = _leaf(result)
    assert "NonExistent" in leaf.message
    assert "values/0" not in leaf.message
    assert leaf.target == "NonExistent"


def test_base_assertion_no_match_ok(mock_file: Any) -> None:
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/NonExistent/values/0",
        operator="=",
        value=42,
        error_if_no_match=False,
    )
    result = assertion.evaluate(mock_file, Severity.INFO)
    leaf = _leaf(result)
    assert "NonExistent" in leaf.message
    assert "not required" in leaf.message
    assert leaf.target == "NonExistent"


# =============================================================================
# ExistsAssertion tests
# =============================================================================


def test_exists_pass_message(mock_file: Any) -> None:
    assertion = ExistsAssertion(check="exists", path="attributes/global_attr")
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert result.valid is True
    assert "global_attr" in result.message
    assert "exists" in result.message
    assert "path" not in result.message.lower()


def test_exists_fail_message(mock_file: Any) -> None:
    assertion = ExistsAssertion(check="exists", path="attributes/Missing")
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert result.valid is False
    assert "Missing" in result.message
    assert result.target == "Missing"


def test_exists_pass_target_is_clean(mock_file: Any) -> None:
    assertion = ExistsAssertion(check="exists", path="attributes/global_attr")
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert result.target == "global_attr"


# =============================================================================
# MatchesAssertion tests
# =============================================================================


def test_matches_fail_message(mock_file: Any) -> None:
    assertion = MatchesAssertion(
        check="matches",
        path="attributes/global_attr/values/0",
        pattern=re.compile("^[a-z]+$"),
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert "expected a string value" in result.message
    assert "path" not in result.message.lower()
    assert result.target == "global_attr"


def test_matches_pass_message() -> None:
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "Source": Attribute(
                name="Source", data_type=[DataType.CHAR], shape=[1], values=["hello"]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = MatchesAssertion(
        check="matches", path="attributes/Source/values/0", pattern=re.compile("^[a-z]+$")
    )
    result = _leaf(assertion.evaluate(f, Severity.WARNING))
    assert result.valid is True
    assert "'hello'" in result.message
    assert "matches" in result.message


def test_matches_custom_message() -> None:
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "Source": Attribute(name="Source", data_type=[DataType.CHAR], shape=[1], values=["BAD"])
        },
        variables={},
        compression="NONE",
    )
    assertion = MatchesAssertion(
        check="matches",
        path="attributes/Source/values/0",
        pattern=re.compile("^[a-z]+$"),
        message="{{ attribute }} '{{ value }}' must be lowercase",
    )
    result = _leaf(assertion.evaluate(f, Severity.WARNING))
    assert result.message == "Source 'BAD' must be lowercase"


# =============================================================================
# ComparisonAssertion / RangeAssertion tests
# =============================================================================


def test_comparison_fail_message(mock_file: Any) -> None:
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/global_attr/values/0",
        operator=">",
        value=100,
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert "does not satisfy" in result.message
    assert "path" not in result.message.lower()
    assert result.target == "global_attr"


def test_comparison_pass_message(mock_file: Any) -> None:
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/global_attr/values/0",
        operator="=",
        value=42,
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert result.valid is True
    assert "satisfies" in result.message


def test_range_fail_message(mock_file: Any) -> None:
    assertion = RangeAssertion(
        check="range",
        path="attributes/global_attr/values/0",
        min=100,
        max=200,
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.WARNING))
    assert "not within range" in result.message
    assert result.target == "global_attr"


def test_range_pass_message(mock_file: Any) -> None:
    assertion = RangeAssertion(
        check="range",
        path="attributes/global_attr/values/0",
        min=0,
        max=100,
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.WARNING))
    assert result.valid is True
    assert "within range" in result.message


# =============================================================================
# Collection assertion tests
# =============================================================================


def test_contains_fail_message(mock_file: Any) -> None:
    assertion = ContainsAssertion(
        check="in",
        path="attributes/global_attr/values/0",
        values=[1, 2, 3],
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert "not in" in result.message.lower()
    assert "path" not in result.message.lower()
    assert result.target == "global_attr"


def test_not_contains_pass_message(mock_file: Any) -> None:
    assertion = NotContainsAssertion(
        check="not_in",
        path="attributes/global_attr/values/0",
        values=[1, 2, 3],
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.WARNING))
    assert result.valid is True
    assert "not in" in result.message.lower()


def test_length_min_fail_message() -> None:
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "TEXT": Attribute(name="TEXT", data_type=[DataType.CHAR], shape=[1], values=["hi"])
        },
        variables={},
        compression="NONE",
    )
    assertion = LengthAssertion(check="length", path="attributes/TEXT/values/0", min=10)
    result = _leaf(assertion.evaluate(f, Severity.WARNING))
    assert "2" in result.message
    assert "10" in result.message
    assert result.target == "TEXT"


def test_not_empty_fail_message() -> None:
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "TEXT": Attribute(name="TEXT", data_type=[DataType.CHAR], shape=[1], values=[""])
        },
        variables={},
        compression="NONE",
    )
    assertion = NotEmptyAssertion(check="not_empty", path="attributes/TEXT/values/0")
    result = _leaf(assertion.evaluate(f, Severity.WARNING))
    assert "empty" in result.message
    assert result.target == "TEXT"


def test_requires_fail_message(mock_file: Any) -> None:
    assertion = RequiresAssertion(check="requires", path="variables", key="MissingVar")
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert "MissingVar" in result.message
    assert "path" not in result.message.lower()


# =============================================================================
# IsTypeAssertion tests
# =============================================================================


def test_is_type_fail_message(mock_file: Any) -> None:
    assertion = IsTypeAssertion(
        check="is_type",
        path="attributes/global_attr/data_type/0",
        type="FLOAT64",
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert "FLOAT64" in result.message
    assert "INT32" in result.message
    assert "path" not in result.message.lower()
    assert result.target == "global_attr"


def test_is_type_pass_message(mock_file: Any) -> None:
    assertion = IsTypeAssertion(
        check="is_type",
        path="attributes/global_attr/data_type/0",
        type="INT32",
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.ERROR))
    assert result.valid is True
    assert "INT32" in result.message
    assert "as expected" in result.message


# =============================================================================
# CompareToAssertion tests
# =============================================================================


def test_compare_to_pass_message(mock_file_with_range: Any) -> None:
    assertion = CompareToAssertion(
        check="compare_to",
        path="variables/{var}/attributes/FILLVAL/values/0",
        operator="<",
        other_path="variables/{var}/attributes/VALIDMIN/values/0",
    )
    result = assertion.evaluate(mock_file_with_range, Severity.WARNING)
    leaf = _leaf(result)
    assert leaf.valid is True
    assert "path" not in leaf.message.lower() or len(leaf.message) < 100
    assert "values/0" not in leaf.target


def test_compare_to_custom_jinja_message(mock_file_with_range: Any) -> None:
    assertion = CompareToAssertion(
        check="compare_to",
        path="variables/{var}/attributes/FILLVAL/values/0",
        operator="<",
        other_path="variables/{var}/attributes/VALIDMIN/values/0",
        message="Variable '{{ var }}': FILLVAL ({{ value }}) must be < VALIDMIN ({{ other_value }})",
    )
    result = assertion.evaluate(mock_file_with_range, Severity.WARNING)
    leaf = _leaf(result)
    assert "var1" in leaf.message
    assert "FILLVAL" in leaf.message


# =============================================================================
# ReferencesVariableAssertion tests
# =============================================================================


def test_ref_variable_not_string_message(mock_file: Any) -> None:
    assertion = ReferencesVariableAssertion(
        check="reference_variable",
        path="attributes/global_attr/values/0",
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.WARNING))
    assert "string" in result.message.lower()
    assert "path" not in result.message.lower()
    assert result.target == "global_attr"


def test_ref_variable_pass_message() -> None:
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "DEPEND_0": Attribute(
                name="DEPEND_0",
                data_type=[DataType.CHAR],
                shape=[1],
                values=["Epoch"],
            )
        },
        variables={
            "Epoch": Variable(
                name="Epoch",
                shape=[10],
                attributes={},
                data_type=DataType.INT64,
                compression="NONE",
                record_variance=True,
            )
        },
        compression="NONE",
    )
    assertion = ReferencesVariableAssertion(
        check="reference_variable",
        path="attributes/DEPEND_0/values/0",
    )
    result = _leaf(assertion.evaluate(f, Severity.WARNING))
    assert result.valid is True
    assert "Epoch" in result.message
    assert "path" not in result.message.lower()


# =============================================================================
# ContainsKeysAssertion tests
# =============================================================================


def test_contains_keys_fail_message(mock_file: Any) -> None:
    assertion = ContainsKeysAssertion(
        check="contains_keys",
        path="variables/var1/attributes",
        keys=frozenset({"CATDESC", "UNITS"}),
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.WARNING))
    assert not result.valid
    assert "CATDESC" in result.message or "UNITS" in result.message
    assert result.target == "var1"


def test_contains_keys_missing_keys_sorted(mock_file: Any) -> None:
    """Missing keys should appear in sorted order for deterministic output."""
    assertion = ContainsKeysAssertion(
        check="contains_keys",
        path="variables/.*/attributes",
        keys=frozenset({"ZEBRA", "APPLE", "MANGO"}),
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = _leaf(result)
    # All three should be missing, and in sorted order
    assert "APPLE" in leaf.message
    idx_a = leaf.message.index("APPLE")
    idx_m = leaf.message.index("MANGO")
    idx_z = leaf.message.index("ZEBRA")
    assert idx_a < idx_m < idx_z


def test_contains_keys_custom_message(mock_file: Any) -> None:
    assertion = ContainsKeysAssertion(
        check="contains_keys",
        path="variables/var1/attributes",
        keys=frozenset({"CATDESC"}),
        message="{% if valid %}Variable {{ variable }} has all required attributes{% else %}Variable {{ variable }} is missing {{ missing_keys | join(', ') }} attribute{% endif %}",
    )
    result = _leaf(assertion.evaluate(mock_file, Severity.WARNING))
    assert result.message == "Variable var1 is missing CATDESC attribute"


# =============================================================================
# Path captures in non-compare_to assertions
# =============================================================================


def test_exists_assertion_with_path_captures(mock_file_with_range: Any) -> None:
    """Path captures like {var} should work in any assertion, not just compare_to."""
    assertion = ExistsAssertion(
        check="exists",
        path="variables/{var}/attributes/VALIDMIN",
        message="{% if valid %}{{ var }} has VALIDMIN{% else %}{{ var }} missing VALIDMIN{% endif %}",
    )
    result = assertion.evaluate(mock_file_with_range, Severity.WARNING)
    leaf = _leaf(result)
    assert "var1" in leaf.message


def test_comparison_assertion_with_path_captures(mock_file_with_range: Any) -> None:
    """Path captures should be available in comparison assertion messages."""
    assertion = ComparisonAssertion(
        check="comparison",
        path="variables/{var}/attributes/VALIDMIN/values/0",
        operator=">=",
        value=0,
        message="{% if valid %}{{ var }} VALIDMIN is non-negative{% else %}{{ var }} VALIDMIN is negative{% endif %}",
    )
    result = assertion.evaluate(mock_file_with_range, Severity.WARNING)
    leaf = _leaf(result)
    assert "var1" in leaf.message
