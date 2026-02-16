from typing import Any, Literal

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, resolve_path


class ContainsKeysAssertion(BaseAssertion):
    check: Literal["contains_keys"] = "contains_keys"
    keys: list[str]

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        if isinstance(value, dict):
            missing_keys = [k for k in self.keys if k not in value]
            if missing_keys:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Value at path '{path}' is missing keys: {missing_keys}",
                                        target=self.path)
            else:
                return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                        message=f"Value at path '{path}' contains all required keys.",
                                        target=self.path)
        else:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Value at path '{path}' is not an object.", target=self.path)
