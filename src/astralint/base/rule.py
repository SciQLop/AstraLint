from pydantic import BaseModel, ConfigDict

from .file import File
from .validation_result import Severity, ValidationResult, ValidationResultGroup


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    description: str
    url: str
    reference: str
    severity: Severity

    def check(self, file: File) -> ValidationResult | ValidationResultGroup: ...

    def _format_result(self, valid: bool, message: str) -> ValidationResult:
        return ValidationResult(
            valid=valid, reference=self.reference, severity=self.severity, message=message
        )


RULES: dict[str, list[Rule]] = {}


class RegisterRule(BaseModel):
    suite: str

    def __call__(self, cls):
        if self.suite not in RULES:
            RULES[self.suite] = []
        RULES[self.suite].append(cls())
        return cls


def get_rules_for_suite(suite: str) -> list[Rule]:
    return RULES.get(suite, [])
