from typing import Any, Protocol

from .validation_result import ValidationResult, Severity


class Rule(Protocol):
    @property
    def description(self) -> str: ...

    @property
    def url(self) -> str: ...

    @property
    def reference(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def severity(self) -> Severity: ...

    def check(self, file: Any) -> list[ValidationResult]: ...

    def _format_result(self, valid:bool, message:str) -> ValidationResult:
        return ValidationResult(
            valid=valid,
            reference=self.reference,
            severity=self.severity,
            message=message
        )
