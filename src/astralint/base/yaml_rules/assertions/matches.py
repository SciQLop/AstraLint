import re
from typing import Literal

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, resolve_path
from .registry import register_assertion


@register_assertion
class MatchesAssertion(BaseAssertion):
    check: Literal["matches"] = "matches"
    pattern: str

    def evaluate(self, file: File) -> ValidationResult:
        matches = resolve_path(file, self.path)
        if not matches:
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=f"Path '{self.path}' did not match any values.",
                target=self.path
            )
        for _, value in matches:
            if not isinstance(value, str):
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=f"Value at path '{self.path}' is not a string.",
                    target=self.path
                )
            if not re.match(self.pattern, value):
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=f"Value at path '{self.path}' does not match pattern '{self.pattern}'.",
                    target=self.path
                )
        return ValidationResult(
            valid=True,
            reference="",
            severity=Severity.INFO,
            message=f"Value at path '{self.path}' matches pattern '{self.pattern}'.",
            target=self.path)
