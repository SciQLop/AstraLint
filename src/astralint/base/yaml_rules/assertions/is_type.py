from typing import Literal, Any

from ...file import File, Variable
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, resolve_path
from ...file import DataType


class IsTypeAssertion(BaseAssertion):
    check: Literal["is_type"] = "is_type"
    type: str

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if not isinstance(value, DataType):
            if isinstance(value, Variable):
                value = value.data_type
            else:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Value at path '{path}' is not a valid DataType, got '{value}'.",
                                        target=path)
        expected_type = DataType(self.type)
        if value != expected_type:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is of type '{value}', expected '{expected_type}'.",
                                    target=path)
        else:
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Value at path '{path}' is of expected type '{expected_type}'.",
                                    target=path)
