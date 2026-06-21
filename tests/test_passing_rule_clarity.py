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
