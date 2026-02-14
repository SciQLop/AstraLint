import re
from typing import Literal

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, resolve_path


class MatchesAssertion(BaseAssertion):
    check: Literal["matches"] = "matches"
    pattern: str

    def single_assertion(self, file: File, path: str, value: str) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=f"Value at path '{path}' is not a string.",
                target=self.path
            )
        elif not re.match(self.pattern, value):
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=f"Value at path '{path}' does not match pattern '{self.pattern}'.",
                target=self.path
            )
        else:
            return ValidationResult(valid=True, reference="",
                                    message=f"Value at path '{path}' matches pattern '{self.pattern}'.",
                                    severity=Severity.INFO)
