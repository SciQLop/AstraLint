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
