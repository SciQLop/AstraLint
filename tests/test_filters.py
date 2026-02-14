import pytest
from astralint.base.conformance_suite import filter_rules


class MockRule:
    def __init__(self, name, reference=None):
        self.name = name
        self.reference = reference or f"REF-{name.upper()}"


@pytest.fixture
def rules():
    return [
        MockRule("GlobalAttributes", "ISTP-001"),
        MockRule("VariableAttributes", "ISTP-002"),
        MockRule("DataTypes", "ISTP-003"),
        MockRule("Compression", "PDS4-001"),
    ]


@pytest.mark.parametrize("select,ignore,expected_names", [
    # Select by exact name
    (["GlobalAttributes"], None, ["GlobalAttributes"]),
    (["GlobalAttributes", "DataTypes"], None, ["GlobalAttributes", "DataTypes"]),

    # Ignore by exact name
    (None, ["Compression"], ["GlobalAttributes", "VariableAttributes", "DataTypes"]),
    (None, ["GlobalAttributes", "VariableAttributes"], ["DataTypes", "Compression"]),

    # Select by regex on name
    ([".*Attributes"], None, ["GlobalAttributes", "VariableAttributes"]),
    (["Global.*", "Data.*"], None, ["GlobalAttributes", "DataTypes"]),

    # Ignore by regex on name
    (None, [".*Attributes"], ["DataTypes", "Compression"]),

    # Select by reference
    (["ISTP-001"], None, ["GlobalAttributes"]),
    (["ISTP-.*"], None, ["GlobalAttributes", "VariableAttributes", "DataTypes"]),

    # Ignore by reference
    (None, ["PDS4-.*"], ["GlobalAttributes", "VariableAttributes", "DataTypes"]),
    (None, ["ISTP-00[12]"], ["DataTypes", "Compression"]),

    # No filter returns all
    (None, None, ["GlobalAttributes", "VariableAttributes", "DataTypes", "Compression"]),

    # Empty lists are falsy, so no filtering occurs
    ([], None, ["GlobalAttributes", "VariableAttributes", "DataTypes", "Compression"]),
    (None, [], ["GlobalAttributes", "VariableAttributes", "DataTypes", "Compression"]),

    # No matches
    (["NonExistent"], None, []),
    (None, [".*"], []),
])
def test_filter_rules(rules, select, ignore, expected_names):
    result = filter_rules(rules, select=select, ignore=ignore)
    assert [r.name for r in result] == expected_names


def test_filter_rules_select_and_ignore_raises(rules):
    """Cannot use both select and ignore at the same time."""
    with pytest.raises(AssertionError):
        filter_rules(rules, select=["rule1"], ignore=["rule2"])

