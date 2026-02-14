from typing import Literal, Any

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion


class ContainsAssertion(BaseAssertion):
    check: Literal["in"] = "in"
    values: list[Any]

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if value in self.values:
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Value at path '{path}' is in the expected list of values.",
                                    target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is not in the expected list of values.",
                                    target=self.path)


class NotContainsAssertion(BaseAssertion):
    check: Literal["not_in"] = "not_in"
    values: list[Any]

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if value not in self.values:
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Value at path '{path}' is not in the list of disallowed values, as expected.",
                                    target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is in the list of disallowed values, which is not expected.",
                                    target=self.path)


class LengthAssertion(BaseAssertion):
    check: Literal["length"] = "length"
    min: int | None = None
    max: int | None = None
    value: int | None = None

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        try:
            length = len(value)
            if self.value is not None:
                if length == self.value:
                    return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                            message=f"Value at path '{path}' has length {length}, as expected.",
                                            target=self.path)
                else:
                    return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                            message=f"Value at path '{path}' has length {length}, expected {self.value}.",
                                            target=self.path)
            else:
                if self.min is not None and length < self.min:
                    return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                            message=f"Value at path '{path}' has length {length}, which is less than minimum {self.min}.",
                                            target=self.path)
                elif self.max is not None and length > self.max:
                    return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                            message=f"Value at path '{path}' has length {length}, which is greater than maximum {self.max}.",
                                            target=self.path)
                else:
                    return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                            message=f"Value at path '{path}' has length {length}, which is within the specified range.",
                                            target=self.path)
        except TypeError:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' does not have a length.", target=self.path)


class NotEmptyAssertion(BaseAssertion):
    check: Literal["not_empty"] = "not_empty"

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        try:
            if len(value) > 0:
                return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                        message=f"Value at path '{path}' is not empty, as expected.", target=self.path)
            else:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Value at path '{path}' is empty, which is not expected.",
                                        target=self.path)
        except TypeError:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' does not have a length.", target=self.path)


class RequiresAssertion(BaseAssertion):
    check: Literal["requires"] = "requires"
    key: str

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if self.key in value:
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Value at path '{path}' contains required key '{self.key}'.",
                                    target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is missing required key '{self.key}'.",
                                    target=self.path)


class ArrayShapeAssertion(BaseAssertion):
    check: Literal["array_shape"] = "array_shape"
    shape: list[int]

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if not isinstance(value, list):
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is not an array.", target=self.path)
        if len(value) != len(self.shape):
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' has length {len(value)}, expected {len(self.shape)}.",
                                    target=self.path)
        for i, (item, expected_length) in enumerate(zip(value, self.shape)):
            if not isinstance(item, list) or len(item) != expected_length:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Item at index {i} in array at path '{path}' has length {len(item)}, expected {expected_length}.",
                                        target=self.path)
        return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                message=f"Array at path '{path}' matches the expected shape.", target=self.path)
