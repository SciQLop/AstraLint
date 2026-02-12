from typing import Any, Protocol
from dataclasses import dataclass

from .validation_result import ValidationResult, Severity
from .file import File


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

    def check(self, file: File) -> list[ValidationResult]: ...

    def _format_result(self, valid: bool, message: str) -> ValidationResult:
        return ValidationResult(
            valid=valid,
            reference=self.reference,
            severity=self.severity,
            message=message
        )


RULES: dict[str,list[Rule]] = {}


@dataclass
class RegisterRule:
    suite: str
    def __call__(self, cls):
        if self.suite not in RULES:
            RULES[self.suite] = []
        RULES[self.suite].append(cls())
        return cls


def get_rules_for_suite(suite: str) -> list[Rule]:
    return RULES.get(suite, [])
