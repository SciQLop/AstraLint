"""Passing validation leaves must read as positive statements, not as the failure
phrasing of the rule. Reproducer for the "✔ … cannot be empty" / "✔ … must follow"
oddity: rule messages without an ``{% if valid %}`` branch render their failure text
verbatim on a passing line."""

from astralint.base import Severity, ValidationResult, get_suite
from astralint.base.file import Attribute, DataType, File, Variable

# Failure-phrasing tells that must never appear on a passing leaf.
_FAILURE_TELLS = (
    "cannot be empty",
    "must follow",
    "must have",
    "must be",
    "must use",
    "should use",
    "should follow",
    "does not",
)


def _attr(name: str, value: str) -> Attribute:
    return Attribute(name=name, data_type=[DataType.CHAR], shape=[1], values=[value])


def _file(global_attrs: dict[str, str], variables: dict[str, Variable] | None = None) -> File:
    return File(
        extension="cdf",
        filename="x.cdf",
        compression="NONE",
        attributes={k: _attr(k, v) for k, v in global_attrs.items()},
        variables=variables or {},
    )


def _rule(name: str):
    suite = get_suite("ISTP")
    assert suite is not None
    return next(r for r in suite.rules if r.name == name)


def _leaves(node):
    if isinstance(node, ValidationResult):
        yield node
    else:
        for child in node.results:
            yield from _leaves(child)


def _passing_messages(group) -> list[str]:
    return [
        leaf.message for leaf in _leaves(group) if leaf.valid and leaf.severity != Severity.SKIPPED
    ]


def _assert_no_failure_phrasing(rule_name: str, messages: list[str]) -> None:
    assert messages, f"{rule_name}: expected at least one passing leaf"
    for message in messages:
        tell = next((t for t in _FAILURE_TELLS if t in message), None)
        assert tell is None, f"{rule_name}: failure phrasing on a passing leaf: {message!r}"


def test_global_attribute_rules_read_positively_on_pass():
    file = _file(
        {
            "Data_type": "L2-Summary>level 2 summary",
            "Project": "ISTP>International Solar-Terrestrial Physics",
            "Descriptor": "EPI>Energetic Particles",
            "Source_name": "GEOTAIL>Geomagnetic Tail",
            "Data_version": "1.0",
            "Logical_source": "geotail_epi_h0",
            "Logical_file_id": "geotail_epi_h0_20200101_v01",
            "TEXT": "Example dataset description.",
            "Generation_date": "20200101",
            "Instrument_type": "Particles (space)",
            "DOI": "https://doi.org/10.1000/abc",
        }
    )
    for rule_name in (
        "DataTypeFormat",
        "ProjectFormat",
        "DescriptorFormat",
        "SourceNameFormat",
        "DataVersionFormat",
        "LogicalSourceFormat",
        "LogicalFileIdFormat",
        "TextNotEmpty",
        "GenerationDateFormat",
        "InstrumentTypeValues",
        "DOIFormat",
    ):
        _assert_no_failure_phrasing(rule_name, _passing_messages(_rule(rule_name).check(file)))


def test_link_count_consistency_reads_positively_on_pass():
    file = _file(
        {
            "HTTP_LINK": "http://example.org",
            "LINK_TEXT": "example",
            "LINK_TITLE": "Example",
        }
    )
    _assert_no_failure_phrasing(
        "LinkCountConsistency", _passing_messages(_rule("LinkCountConsistency").check(file))
    )


def _data_var() -> Variable:
    keys = ["VAR_TYPE", "DEPEND_0", "DISPLAY_TYPE", "VALIDMIN", "VALIDMAX", "LABLAXIS", "UNITS"]
    attrs = {k: _attr(k, "data" if k == "VAR_TYPE" else "x") for k in keys}
    return Variable(
        name="Bx",
        attributes=attrs,
        compression="NONE",
        data_type=DataType.FLOAT32,
        record_variance=True,
        shape=[10],
    )


def test_data_variable_member_messages_read_positively_on_pass():
    group = _rule("DataVariableAttributes").check(_file({}, {"Bx": _data_var()}))
    messages = _passing_messages(group)
    _assert_no_failure_phrasing("DataVariableAttributes", messages)
    assert any("has LABLAXIS or LABL_PTR_1" in m for m in messages)
    assert any("has UNITS or UNIT_PTR" in m for m in messages)


def test_positive_phrasings_are_specific():
    file = _file({"Data_type": "L2-Summary>level 2 summary"})
    messages = _passing_messages(_rule("DataTypeFormat").check(file))
    assert any("Data_type follows" in m for m in messages)
    assert any("Data_type is present" in m for m in messages)
