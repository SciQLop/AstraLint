from ...file import File
from ...validation_result import ValidationResult, Severity
from .base import BaseAssertion, flatten_object, resolve_path
from .registry import register_assertion
from typing import Literal


@register_assertion
class ContainsKeysAssertion(BaseAssertion):
    check: Literal["contains_keys"] = "contains_keys"
    keys: list[str]

    def evaluate(self, file: File) -> ValidationResult:
        matches = resolve_path(file, self.path)
        if not matches:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Path '{self.path}' did not match any values.", target=self.path)
        for _, value in matches:
            if isinstance(value, dict):
                missing_keys = [k for k in self.keys if k not in value]
                if missing_keys:
                    return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                            message=f"Value at path '{self.path}' is missing keys: {missing_keys}",
                                            target=self.path)
            else:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Value at path '{self.path}' is not an object.", target=self.path)
        return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                message=f"Value at path '{self.path}' contains all required keys.", target=self.path)
