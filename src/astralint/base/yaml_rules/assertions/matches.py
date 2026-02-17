import re
from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion


class MatchesAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["matches"] = "matches"  # type: ignore[assignment]
    pattern: re.Pattern

    def single_assertion(self, file: File, path: str, value: str, severity: Severity) -> ValidationResult:
        print(f"Checking if value at path '{path}' matches pattern '{self.pattern.pattern}'...")
        if not isinstance(value, str):
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=f"Value at path '{path}' is not a string.",
                target=self.path,
            )
        elif not re.match(self.pattern, value):
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=f"Value ({value}) at path '{path}' does not match pattern '{self.pattern.pattern}'.",
                target=self.path,
            )
        else:
            return ValidationResult(
                valid=True,
                reference="",
                message=f"Value ({value}) at path '{path}' matches pattern '{self.pattern.pattern}'.",
                severity=severity,
                target=self.path,
            )
