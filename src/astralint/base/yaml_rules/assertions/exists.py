from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, resolve_path


class ExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["exists"] = "exists"  # type: ignore[assignment]

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        if matches:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=f"Path '{self.path}' exists in the file.",
                target=self.path,
            )
        else:
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=f"Path '{self.path}' does not exist in the file.",
                target=self.path,
            )


class NotExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_exists"] = "not_exists"  # type: ignore[assignment]

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        if matches:
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=f"Path '{self.path}' exists in the file but should not.",
                target=self.path,
            )
        else:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=f"Path '{self.path}' does not exist in the file as expected.",
                target=self.path,
            )
