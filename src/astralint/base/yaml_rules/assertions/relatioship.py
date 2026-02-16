from typing import Any, Literal

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, resolve_path


# Value references another variable name
class ReferencesVariableAssertion(BaseAssertion):
    check: Literal["reference_variable"] = "reference_variable"
    variable: str

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if type(value) is str:
            if value in file.variables:
                return ValidationResult(valid=True, reference=file.variables[value], severity=Severity.INFO,
                                        message=f"Value at path '{path}' references variable '{value}'.",
                                        target=self.path)
            else:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Value at path '{path}' references variable '{value}', which is not defined.",
                                        target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is not a string and cannot reference a variable.",
                                    target=self.path)
