from typing import Literal

from pydantic import ConfigDict, Field

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import (
    BaseEvaluable,
    interpolate_captures,
    resolve_path,
    resolve_path_with_captures,
)

_operators = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


class CompareToAssertion(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    check: Literal["compare_to"] = "compare_to"  # type: ignore[assignment]
    path: str
    operator: Literal["=", "!=", "<", "<=", ">", ">="]
    other_path: str
    error_if_no_match: bool = Field(default=True)
    message: str = Field(default="")

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path_with_captures(file, self.path)
        if not matches:
            if self.error_if_no_match:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=f"Path '{self.path}' did not match any values.",
                    target=self.path,
                )
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.INFO,
                message=f"Path '{self.path}' did not match any values, but that's okay.",
                target=self.path,
            )

        results: list[ValidationResult | ValidationResultGroup] = []
        for path, value, captures in matches:
            resolved_other = interpolate_captures(self.other_path, captures)
            other_matches = resolve_path(file, resolved_other)
            if not other_matches:
                results.append(
                    ValidationResult(
                        valid=False,
                        reference="",
                        severity=severity,
                        message=interpolate_captures(
                            self.message or f"Other path '{resolved_other}' not found.",
                            captures,
                        ),
                        target=path,
                    )
                )
                continue

            other_value = other_matches[0][1]
            try:
                passed = _operators[self.operator](value, other_value)
            except TypeError:
                passed = False

            msg = interpolate_captures(
                self.message
                or f"Value at '{path}' ({value}) {self.operator} value at '{resolved_other}' ({other_value}): {'pass' if passed else 'fail'}.",
                captures,
            )
            results.append(
                ValidationResult(
                    valid=passed,
                    reference="",
                    severity=severity,
                    message=msg,
                    target=path,
                )
            )

        return ValidationResultGroup(
            name="CompareToAssertion",
            rule_reference="",
            results=results,
            severity=severity,
        )
