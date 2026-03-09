from typing import Any, Literal

from pydantic import ConfigDict

from ...file import DataType, File, Variable
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class IsTypeAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["is_type"] = "is_type"  # type: ignore[assignment]
    type: str

    _default_template: str = "{% if valid %}type is '{{ expected_type }}' as expected{% else %}type is '{{ actual_type }}', expected '{{ expected_type }}'{% endif %}"
    _not_datatype_template: str = "value is not a valid DataType, got '{{ value }}'"

    def single_assertion(
        self,
        file: File,
        path: str,
        value: Any,
        severity: Severity,
        captures: dict[str, str] | None = None,
    ) -> ValidationResult:
        target = clean_target(path)
        if not isinstance(value, DataType):
            if isinstance(value, Variable):
                value = value.data_type
            else:
                ctx = build_context(target, path, value, valid=False, **(captures or {}))
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=render_message(self._not_datatype_template, ctx),
                    target=target,
                )
        expected_type = DataType(self.type)
        passed = value == expected_type
        ctx = build_context(
            target,
            path,
            value,
            valid=passed,
            expected_type=expected_type,
            actual_type=value,
            **(captures or {}),
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
