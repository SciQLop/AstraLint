from typing import Any, Literal

from pydantic import ConfigDict

from ...file import DataType, File, Variable
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class IsTypeAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["is_type"] = "is_type"  # type: ignore[assignment]
    type: str

    _default_pass_template: str = "type is '{{ expected_type }}' as expected"
    _default_fail_template: str = "type is '{{ actual_type }}', expected '{{ expected_type }}'"
    _not_datatype_template: str = "value is not a valid DataType, got '{{ value }}'"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        if not isinstance(value, DataType):
            if isinstance(value, Variable):
                value = value.data_type
            else:
                ctx = build_context(target, path, value)
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=render_message(self._not_datatype_template, ctx),
                    target=target,
                )
        expected_type = DataType(self.type)
        ctx = build_context(target, path, value, expected_type=expected_type, actual_type=value)
        passed = value == expected_type
        template = self.message or (
            self._default_pass_template if passed else self._default_fail_template
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )
