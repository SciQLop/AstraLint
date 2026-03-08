import pytest

from astralint.base.yaml_rules.assertions.base import clean_target, render_message


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
def test_clean_target(raw_path, expected):
    assert clean_target(raw_path) == expected


def test_render_message_simple():
    result = render_message("'{{ value }}' does not match", {"value": "hello"})
    assert result == "'hello' does not match"


def test_render_message_with_filter():
    result = render_message(
        "{{ values | join(', ') }}", {"values": ["a", "b", "c"]}
    )
    assert result == "a, b, c"


def test_render_message_with_none_default():
    result = render_message(
        "{{ attribute or 'unknown' }} is empty", {"attribute": None}
    )
    assert result == "unknown is empty"


def test_render_message_with_attribute():
    result = render_message(
        "{{ attribute or path }} is empty", {"attribute": "CATDESC", "path": "x/y"}
    )
    assert result == "CATDESC is empty"


from astralint.base.yaml_rules.assertions.comparisons import ComparisonAssertion
from astralint.base.validation_result import Severity


def test_base_assertion_no_match_message(mock_file):
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/NonExistent/values/0",
        operator="=",
        value=42,
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert "NonExistent" in result.message
    assert "values/0" not in result.message
    assert result.target == "NonExistent"


def test_base_assertion_no_match_ok(mock_file):
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/NonExistent/values/0",
        operator="=",
        value=42,
        error_if_no_match=False,
    )
    result = assertion.evaluate(mock_file, Severity.INFO)
    assert "NonExistent" in result.message
    assert "not required" in result.message
    assert result.target == "NonExistent"


from astralint.base.yaml_rules.assertions.exists import ExistsAssertion


def test_exists_pass_message(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/global_attr")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert result.valid is True
    assert "global_attr" in result.message
    assert "exists" in result.message
    assert "path" not in result.message.lower()


def test_exists_fail_message(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/Missing")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert result.valid is False
    assert "Missing" in result.message
    assert result.target == "Missing"


def test_exists_pass_target_is_clean(mock_file):
    assertion = ExistsAssertion(check="exists", path="attributes/global_attr")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    assert result.target == "global_attr"


from astralint.base.yaml_rules.assertions.matches import MatchesAssertion
from astralint.base.file import Attribute, DataType, File


def test_matches_fail_message(mock_file):
    assertion = MatchesAssertion(
        check="matches",
        path="attributes/global_attr/values/0",
        pattern="^[a-z]+$",
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "expected a string value" in leaf.message
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_matches_pass_message():
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
        check="matches", path="attributes/Source/values/0", pattern="^[a-z]+$"
    )
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.valid is True
    assert "'hello'" in leaf.message
    assert "matches" in leaf.message


def test_matches_custom_message():
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "Source": Attribute(
                name="Source", data_type=[DataType.CHAR], shape=[1], values=["BAD"]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = MatchesAssertion(
        check="matches",
        path="attributes/Source/values/0",
        pattern="^[a-z]+$",
        message="{{ attribute }} '{{ value }}' must be lowercase",
    )
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.message == "Source 'BAD' must be lowercase"


from astralint.base.yaml_rules.assertions.comparisons import RangeAssertion


def test_comparison_fail_message(mock_file):
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/global_attr/values/0",
        operator=">",
        value=100,
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "does not satisfy" in leaf.message
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_comparison_pass_message(mock_file):
    assertion = ComparisonAssertion(
        check="comparison",
        path="attributes/global_attr/values/0",
        operator="=",
        value=42,
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.valid is True
    assert "satisfies" in leaf.message


def test_range_fail_message(mock_file):
    assertion = RangeAssertion(
        check="range",
        path="attributes/global_attr/values/0",
        min=100,
        max=200,
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "not within range" in leaf.message
    assert leaf.target == "global_attr"


def test_range_pass_message(mock_file):
    assertion = RangeAssertion(
        check="range",
        path="attributes/global_attr/values/0",
        min=0,
        max=100,
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.valid is True
    assert "within range" in leaf.message


from astralint.base.yaml_rules.assertions.collections import (
    ContainsAssertion,
    LengthAssertion,
    NotContainsAssertion,
    NotEmptyAssertion,
    RequiresAssertion,
)


def test_contains_fail_message(mock_file):
    assertion = ContainsAssertion(
        check="in",
        path="attributes/global_attr/values/0",
        values=[1, 2, 3],
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "not in" in leaf.message.lower()
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_not_contains_pass_message(mock_file):
    assertion = NotContainsAssertion(
        check="not_in",
        path="attributes/global_attr/values/0",
        values=[1, 2, 3],
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.valid is True
    assert "not in" in leaf.message.lower()


def test_length_min_fail_message():
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "TEXT": Attribute(
                name="TEXT", data_type=[DataType.CHAR], shape=[1], values=["hi"]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = LengthAssertion(check="length", path="attributes/TEXT/values/0", min=10)
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "2" in leaf.message
    assert "10" in leaf.message
    assert leaf.target == "TEXT"


def test_not_empty_fail_message():
    f = File(
        extension="mock",
        filename="test.mock",
        attributes={
            "TEXT": Attribute(
                name="TEXT", data_type=[DataType.CHAR], shape=[1], values=[""]
            )
        },
        variables={},
        compression="NONE",
    )
    assertion = NotEmptyAssertion(check="not_empty", path="attributes/TEXT/values/0")
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "empty" in leaf.message
    assert leaf.target == "TEXT"


def test_requires_fail_message(mock_file):
    assertion = RequiresAssertion(check="requires", path="variables", key="MissingVar")
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "MissingVar" in leaf.message
    assert "path" not in leaf.message.lower()


from astralint.base.yaml_rules.assertions.is_type import IsTypeAssertion


def test_is_type_fail_message(mock_file):
    # mock_file has global_attr with data_type=[DataType.INT32]
    assertion = IsTypeAssertion(
        check="is_type",
        path="attributes/global_attr/data_type/0",
        type="FLOAT64",
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "FLOAT64" in leaf.message
    assert "INT32" in leaf.message
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_is_type_pass_message(mock_file):
    assertion = IsTypeAssertion(
        check="is_type",
        path="attributes/global_attr/data_type/0",
        type="INT32",
    )
    result = assertion.evaluate(mock_file, Severity.ERROR)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.valid is True
    assert "INT32" in leaf.message
    assert "as expected" in leaf.message


from astralint.base.yaml_rules.assertions.relatioship import ReferencesVariableAssertion


def test_ref_variable_not_string_message(mock_file):
    # mock_file global_attr value is 42 (int), not a string
    assertion = ReferencesVariableAssertion(
        check="reference_variable",
        path="attributes/global_attr/values/0",
    )
    result = assertion.evaluate(mock_file, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert "string" in leaf.message.lower()
    assert "path" not in leaf.message.lower()
    assert leaf.target == "global_attr"


def test_ref_variable_pass_message(mock_file):
    # mock_file has variable "var1", create a file where an attribute value references it
    from astralint.base.file import Attribute, DataType, File, Variable

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
    result = assertion.evaluate(f, Severity.WARNING)
    leaf = result.results[0] if hasattr(result, "results") else result
    assert leaf.valid is True
    assert "Epoch" in leaf.message
    assert "path" not in leaf.message.lower()
