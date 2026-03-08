from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message

_yaml_types = int | float | bool | list | str

_operators = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


class ComparisonAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["comparison"] = "comparison"  # type: ignore[assignment]
    operator: Literal["=", "!=", "<", "<=", ">", ">="]
    value: _yaml_types

    _default_pass_template: str = "{{ value }} satisfies {{ operator }} {{ expected }}"
    _default_fail_template: str = "{{ value }} does not satisfy {{ operator }} {{ expected }}"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, operator=self.operator, expected=self.value)
        passed = _operators[self.operator](value, self.value)
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


class RangeAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["range"] = "range"  # type: ignore[assignment]
    min: _yaml_types
    max: _yaml_types

    _default_pass_template: str = "{{ value }} is within range [{{ min }}, {{ max }}]"
    _default_fail_template: str = "{{ value }} is not within range [{{ min }}, {{ max }}]"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, min=self.min, max=self.max)
        passed = self.min <= value <= self.max
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
