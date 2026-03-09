from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class ReferencesVariableAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["reference_variable"] = "reference_variable"  # type: ignore[assignment]
    variable: str | None = None

    _default_template: str = "{% if valid %}references existing variable '{{ value }}'{% else %}{% if expected_variable is not none and value != expected_variable %}is '{{ value }}', expected reference to '{{ expected_variable }}'{% else %}references undefined variable '{{ value }}'{% endif %}{% endif %}"
    _not_string_template: str = "expected a string value to reference a variable"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, valid=False, expected_variable=self.variable, **(captures or {}))

        if type(value) is not str:
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self.message or self._not_string_template, ctx),
                target=target,
            )

        if self.variable is not None:
            if value == self.variable and value in file.variables:
                passed = True
            else:
                passed = False
        else:
            passed = value in file.variables

        ctx["valid"] = passed
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
