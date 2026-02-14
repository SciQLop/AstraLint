from typing import Literal, Any

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion

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
    check: Literal["comparison"] = "comparison"
    operator: Literal["=", "!=", "<", "<=", ">", ">="]
    value: _yaml_types

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if _operators[self.operator](value, self.value):
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Value at path '{path}' satisfies condition '{value} {self.operator} {self.value}'.",
                                    target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' does not satisfy condition '{value} {self.operator} {self.value}'.",
                                    target=self.path)


class RangeAssertion(BaseAssertion):
    check: Literal["range"] = "range"
    min: _yaml_types
    max: _yaml_types

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if self.min <= value <= self.max:
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Value at path '{path}' is within range [{self.min}, {self.max}].",
                                    target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is not within range [{self.min}, {self.max}].",
                                    target=self.path)
