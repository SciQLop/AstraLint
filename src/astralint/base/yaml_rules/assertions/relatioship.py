from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class ReferencesVariableAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["reference_variable"] = "reference_variable"  # type: ignore[assignment]
    variable: str | None = None

    _pass_specific_template: str = "correctly references variable '{{ value }}'"
    _pass_any_template: str = "references existing variable '{{ value }}'"
    _fail_undefined_template: str = "references undefined variable '{{ value }}'"
    _fail_wrong_var_template: str = (
        "is '{{ value }}', expected reference to '{{ expected_variable }}'"
    )
    _not_string_template: str = "expected a string value to reference a variable"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, expected_variable=self.variable)

        if type(value) is not str:
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self.message or self._not_string_template, ctx),
                target=target,
            )

        if self.variable is not None:
            if value == self.variable:
                if value in file.variables:
                    return ValidationResult(
                        valid=True,
                        reference="",
                        severity=severity,
                        message=render_message(
                            self.message or self._pass_specific_template, ctx
                        ),
                        target=target,
                    )
                else:
                    return ValidationResult(
                        valid=False,
                        reference="",
                        severity=severity,
                        message=render_message(
                            self.message or self._fail_undefined_template, ctx
                        ),
                        target=target,
                    )
            else:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message=render_message(
                        self.message or self._fail_wrong_var_template, ctx
                    ),
                    target=target,
                )

        if value in file.variables:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=render_message(self.message or self._pass_any_template, ctx),
                target=target,
            )
        else:
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(
                    self.message or self._fail_undefined_template, ctx
                ),
                target=target,
            )
