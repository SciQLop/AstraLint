from typing import Literal, Any
from pydantic import model_validator

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertionGroup, BaseEvaluable, get_assertion_union


class AllOf(BaseAssertionGroup):
    check: Literal["all_of"] = "all_of"

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if not result.valid:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Assertion failed in 'all_of'", target="")
        return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                message=f"All assertions in 'all_of' passed successfully.", target="")


class AnyOf(BaseAssertionGroup):
    check: Literal["any_of"] = "any_of"

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if result.valid:
                return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                        message=f"At least one assertion in 'any_of' passed successfully.",
                                        target="")
        return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                message=f"All assertions in 'any_of' failed.", target="")


class NoneOf(BaseAssertionGroup):
    check: Literal["none_of"] = "none_of"

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if result.valid:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"At least one assertion in 'none_of' passed, which is not expected",
                                        target="")
        return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                message=f"All assertions in 'none_of' failed as expected.", target="")


class Not(BaseEvaluable):
    check: Literal["not"] = "not"
    assertion: Any

    @model_validator(mode="before")
    @classmethod
    def parse_assertion(cls, data: dict) -> dict:
        """Parse assertion using the discriminated union."""
        assertion_union = get_assertion_union()
        from pydantic import TypeAdapter
        adapter = TypeAdapter(assertion_union)
        if "assertion" in data:
            data["assertion"] = adapter.validate_python(data["assertion"])
        return data

    def evaluate(self, file: File) -> ValidationResult:
        result = self.assertion.evaluate(file)
        if result.valid:
            return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                    message=f"Assertion passed but was expected to fail in 'not'", target="")
        return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                message=f"Assertion failed as expected in 'not'.", target="")
