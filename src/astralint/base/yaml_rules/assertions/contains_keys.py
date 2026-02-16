from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion


class ContainsKeysAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["contains_keys"] = "contains_keys"  # type: ignore[assignment]
    keys: list[str]

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if isinstance(value, dict):
            missing_keys = [k for k in self.keys if k not in value]
            if missing_keys:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=f"Value at path '{path}' is missing keys: {missing_keys}",
                    target=self.path,
                )
            else:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=Severity.INFO,
                    message=f"Value at path '{path}' contains all required keys.",
                    target=self.path,
                )
        else:
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=f"Value at path '{path}' is not an object.",
                target=self.path,
            )
