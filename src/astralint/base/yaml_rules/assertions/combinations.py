from typing import Literal, Any

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion


class AllOf(BaseAssertion):
    check: Literal["all_of"] = "all_of"
    assertions: list[BaseAssertion]

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if not result.valid:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Assertion failed in 'all_of': {result.message}", target=self.path)
        return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                message=f"All assertions in 'all_of' passed successfully.", target=self.path)


class AnyOf(BaseAssertion):
    check: Literal["any_of"] = "any_of"
    assertions: list[BaseAssertion]

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if result.valid:
                return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                        message=f"At least one assertion in 'any_of' passed successfully.",
                                        target=self.path)
        return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                message=f"All assertions in 'any_of' failed.", target=self.path)


class Not(BaseAssertion):
    check: Literal["not"] = "not"
    assertions: list[BaseAssertion]

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if result.valid:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Assertion failed in 'not': {result.message}", target=self.path)
        return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                message=f"All assertions in 'not' failed as expected.", target=self.path)
