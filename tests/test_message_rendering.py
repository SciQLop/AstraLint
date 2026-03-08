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
