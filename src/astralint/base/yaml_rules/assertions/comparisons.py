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

    _default_template: str = "{% if valid %}{{ value }} satisfies {{ operator }} {{ expected }}{% else %}{{ value }} does not satisfy {{ operator }} {{ expected }}{% endif %}"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        passed = _operators[self.operator](value, self.value)
        ctx = build_context(
            target, path, value, valid=passed, operator=self.operator, expected=self.value
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )


class RangeAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["range"] = "range"  # type: ignore[assignment]
    min: _yaml_types
    max: _yaml_types

    _default_template: str = "{% if valid %}{{ value }} is within range [{{ min }}, {{ max }}]{% else %}{{ value }} is not within range [{{ min }}, {{ max }}]{% endif %}"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        passed = self.min <= value <= self.max
        ctx = build_context(target, path, value, valid=passed, min=self.min, max=self.max)
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
