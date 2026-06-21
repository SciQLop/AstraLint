# tests/test_passing_rule_clarity.py
from pydantic import TypeAdapter

from astralint.base import ValidationResult, ValidationResultGroup
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.base.validation_result import Severity
from astralint.base.yaml_rules.assertions.base import get_assertion_union

_adapter = TypeAdapter(get_assertion_union())


def _attr(name: str, value: str) -> Attribute:
    return Attribute(name=name, data_type=[DataType.CHAR], shape=[1], values=[value])


def _file_with_var(attrs: dict[str, str]) -> File:
    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "Bx": Variable(
                name="Bx",
                attributes={k: _attr(k, v) for k, v in attrs.items()},
                compression="NONE",
                data_type=DataType.FLOAT32,
                record_variance=True,
                shape=[10],
            )
        },
    )


def _leaf_messages(node):
    if isinstance(node, ValidationResult):
        return [node.message]
    out = []
    for child in node.results:
        out += _leaf_messages(child)
    return out


def test_all_of_pass_preserves_each_member():
    assertion = _adapter.validate_python(
        {
            "check": "all_of",
            "assertions": [
                {
                    "check": "exists",
                    "path": "variables/Bx/attributes/LABLAXIS",
                    "message": "{% if valid %}LABLAXIS present{% else %}missing{% endif %}",
                },
                {
                    "check": "exists",
                    "path": "variables/Bx/attributes/UNITS",
                    "message": "{% if valid %}UNITS present{% else %}missing{% endif %}",
                },
            ],
        }
    )
    result = assertion.evaluate(_file_with_var({"LABLAXIS": "B", "UNITS": "nT"}), Severity.ERROR)
    assert result.valid
    messages = _leaf_messages(result)
    assert "LABLAXIS present" in messages
    assert "UNITS present" in messages
    assert "All assertions in 'all_of' passed successfully." not in messages


def test_any_of_pass_reports_the_passing_alternative_target():
    assertion = _adapter.validate_python(
        {
            "check": "any_of",
            "message": "must have LABLAXIS or LABL_PTR_1",
            "assertions": [
                {"check": "exists", "path": "variables/Bx/attributes/LABLAXIS", "message": ""},
                {"check": "exists", "path": "variables/Bx/attributes/LABL_PTR_1", "message": ""},
            ],
        }
    )
    result = assertion.evaluate(_file_with_var({"LABLAXIS": "B"}), Severity.ERROR)
    assert result.valid
    assert result.message == "must have LABLAXIS or LABL_PTR_1"
    assert "LABLAXIS" in result.target


from astralint.reports._findings import display_children, is_internal_wrapper


def test_display_children_flattens_stamps_reference_and_drops_noise():
    skipped = ValidationResult(
        valid=True,
        reference="",
        severity=Severity.SKIPPED,
        message="Condition not met, assertion skipped.",
        target="",
    )
    not_required = ValidationResult(
        valid=True,
        reference="",
        severity=Severity.INFO,
        message="DOI did not match any values (not required)",
        target="DOI",
    )
    real = ValidationResult(
        valid=True,
        reference="",
        severity=Severity.ERROR,
        message="Data_type is valid",
        target="Data_type",
        value="L2>level 2",
    )
    wrapper = ValidationResultGroup(
        name="Matches",
        rule_reference="",
        severity=Severity.ERROR,
        results=[real, skipped, not_required],
    )
    rule = ValidationResultGroup(
        name="DataTypeFormat",
        rule_reference="ISTP-GA-006",
        severity=Severity.ERROR,
        results=[wrapper],
        url="http://example/doc",
    )
    children = display_children(rule)
    assert all(isinstance(c, ValidationResult) for c in children)
    assert [c.message for c in children] == ["Data_type is valid"]
    leaf = children[0]
    assert isinstance(leaf, ValidationResult)
    assert leaf.reference == "ISTP-GA-006"  # stamped from the rule group


def test_is_internal_wrapper():
    assert is_internal_wrapper(
        ValidationResultGroup(name="all_of", rule_reference="", severity=Severity.ERROR, results=[])
    )
    assert not is_internal_wrapper(
        ValidationResultGroup(
            name="r", rule_reference="ISTP-GA-006", severity=Severity.ERROR, results=[]
        )
    )


from astralint.reports.html import generate_html_fragment


def _passing_rule_tree() -> ValidationResultGroup:
    real = ValidationResult(
        valid=True,
        reference="",
        severity=Severity.ERROR,
        message="Data_type is valid",
        target="Data_type",
        value="L2>level 2",
    )
    not_required = ValidationResult(
        valid=True,
        reference="",
        severity=Severity.INFO,
        message="DOI did not match any values (not required)",
        target="DOI",
    )
    wrapper = ValidationResultGroup(
        name="Matches",
        rule_reference="",
        severity=Severity.ERROR,
        results=[real, not_required],
    )
    return ValidationResultGroup(
        name="DataTypeFormat",
        rule_reference="ISTP-GA-006",
        severity=Severity.ERROR,
        results=[wrapper],
    )


def test_html_passing_rule_shows_reference_and_drops_not_required():
    html = generate_html_fragment(_passing_rule_tree())
    assert "ISTP-GA-006" in html
    assert "Data_type is valid" in html
    assert "not required" not in html


from rich.console import Console

from astralint.reports.console import console_report


def _render_to_text(tree: ValidationResultGroup) -> str:
    console = Console(width=200, record=True, color_system=None)
    console_report(tree, console)
    return console.export_text()


def test_console_show_passed_stamps_reference_and_drops_noise():
    out = _render_to_text(_passing_rule_tree())
    assert "ISTP-GA-006" in out
    assert "Data_type is valid" in out
    assert "not required" not in out
    assert "✔ :" not in out  # no empty-reference leaf
