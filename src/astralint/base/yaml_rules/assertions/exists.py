from typing import Literal

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, resolve_path


class ExistsAssertion(BaseAssertion):
    check: Literal["exists"] = "exists"

    def evaluate(self, file: File) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        if matches:
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Path '{self.path}' exists in the file.", target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Path '{self.path}' does not exist in the file.", target=self.path)


class NotExistsAssertion(BaseAssertion):
    check: Literal["not_exists"] = "not_exists"

    def evaluate(self, file: File) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        if matches:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Path '{self.path}' exists in the file but should not.", target=self.path)
        else:
            return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                    message=f"Path '{self.path}' does not exist in the file as expected.",
                                    target=self.path)
