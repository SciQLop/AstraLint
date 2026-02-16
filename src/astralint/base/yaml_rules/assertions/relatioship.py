from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion


# Value references another variable name
class ReferencesVariableAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["reference_variable"] = "reference_variable"  # type: ignore[assignment]
    variable: str | None = None  # Optional: if specified, check for specific variable

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if type(value) is str:
            # If variable is specified, check for that specific variable
            if self.variable is not None:
                if value == self.variable:
                    if value in file.variables:
                        return ValidationResult(
                            valid=True,
                            reference="",
                            severity=Severity.INFO,
                            message=f"Value at path '{path}' correctly references variable '{value}'.",
                            target=self.path,
                        )
                    else:
                        return ValidationResult(
                            valid=False,
                            reference="",
                            severity=Severity.ERROR,
                            message=f"Value at path '{path}' references variable '{value}', which is not defined.",
                            target=self.path,
                        )
                else:
                    return ValidationResult(
                        valid=False,
                        reference="",
                        severity=Severity.ERROR,
                        message=f"Value at path '{path}' is '{value}', expected reference to '{self.variable}'.",
                        target=self.path,
                    )
            # Otherwise, just check if the value references any existing variable
            if value in file.variables:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=Severity.INFO,
                    message=f"Value at path '{path}' references existing variable '{value}'.",
                    target=self.path,
                )
            else:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=f"Value at path '{path}' references variable '{value}', which is not defined.",
                    target=self.path,
                )
        else:
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=f"Value at path '{path}' is not a string and cannot reference a variable.",
                target=self.path,
            )
