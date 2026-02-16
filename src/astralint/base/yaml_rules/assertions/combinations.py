from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertionGroup, BaseEvaluable, get_assertion_union


class AllOf(BaseAssertionGroup):
    model_config = ConfigDict(frozen=True)
    check: Literal["all_of"] = "all_of"  # type: ignore[assignment]

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if not result.valid:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message="Assertion failed in 'all_of'",
                    target="",
                )
        return ValidationResult(
            valid=True,
            reference="",
            severity=Severity.INFO,
            message="All assertions in 'all_of' passed successfully.",
            target="",
        )


class AnyOf(BaseAssertionGroup):
    model_config = ConfigDict(frozen=True)
    check: Literal["any_of"] = "any_of"  # type: ignore[assignment]

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if result.valid:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=Severity.INFO,
                    message="At least one assertion in 'any_of' passed successfully.",
                    target="",
                )
        return ValidationResult(
            valid=False,
            reference="",
            severity=Severity.ERROR,
            message="All assertions in 'any_of' failed.",
            target="",
        )


class NoneOf(BaseAssertionGroup):
    model_config = ConfigDict(frozen=True)
    check: Literal["none_of"] = "none_of"  # type: ignore[assignment]

    def evaluate(self, file: File) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file)
            if result.valid:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message="At least one assertion in 'none_of' passed, which is not expected",
                    target="",
                )
        return ValidationResult(
            valid=True,
            reference="",
            severity=Severity.INFO,
            message="All assertions in 'none_of' failed as expected.",
            target="",
        )


class Not(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    check: Literal["not"] = "not"  # type: ignore[assignment]
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
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message="Assertion passed but was expected to fail in 'not'",
                target="",
            )
        return ValidationResult(
            valid=True,
            reference="",
            severity=Severity.INFO,
            message="Assertion failed as expected in 'not'.",
            target="",
        )


class IfThen(BaseEvaluable):
    """Conditional assertion: if condition passes, then assertion must pass.
    If condition fails, the assertion is skipped (vacuously true)."""

    model_config = ConfigDict(frozen=True)
    check: Literal["if_then"] = "if_then"  # type: ignore[assignment]
    if_: Any = Field(alias="if")
    then: Any

    @model_validator(mode="before")
    @classmethod
    def parse_assertions(cls, data: dict) -> dict:
        """Parse if and then assertions using the discriminated union."""
        assertion_union = get_assertion_union()
        from pydantic import TypeAdapter

        adapter = TypeAdapter(assertion_union)
        if "if" in data:
            data["if"] = adapter.validate_python(data["if"])
        if "then" in data:
            data["then"] = adapter.validate_python(data["then"])
        return data

    def evaluate(self, file: File) -> ValidationResult:
        condition_result = self.if_.evaluate(file)
        if not condition_result.valid:
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.SKIPPED,
                message="Condition not met, assertion skipped.",
                target="",
            )
        then_result = self.then.evaluate(file)
        if then_result.valid:
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.INFO,
                message="Condition met and assertion passed.",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=Severity.ERROR,
            message="Condition met but assertion failed.",
            target="",
        )


class IfThenElse(BaseEvaluable):
    """Conditional assertion with else branch: if condition passes, run then; otherwise run else."""

    model_config = ConfigDict(frozen=True)
    check: Literal["if_then_else"] = "if_then_else"  # type: ignore[assignment]
    if_: Any = Field(alias="if")
    then: Any
    else_: Any = Field(alias="else")

    @model_validator(mode="before")
    @classmethod
    def parse_assertions(cls, data: dict) -> dict:
        """Parse if, then, and else assertions using the discriminated union."""
        assertion_union = get_assertion_union()
        from pydantic import TypeAdapter

        adapter = TypeAdapter(assertion_union)
        if "if" in data:
            data["if"] = adapter.validate_python(data["if"])
        if "then" in data:
            data["then"] = adapter.validate_python(data["then"])
        if "else" in data:
            data["else"] = adapter.validate_python(data["else"])
        return data

    def evaluate(self, file: File) -> ValidationResult:
        condition_result = self.if_.evaluate(file)
        if condition_result.valid:
            then_result = self.then.evaluate(file)
            if then_result.valid:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=Severity.INFO,
                    message="Condition met and 'then' assertion passed.",
                    target="",
                )
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message="Condition met but 'then' assertion failed.",
                target="",
            )
        else:
            else_result = self.else_.evaluate(file)
            if else_result.valid:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=Severity.INFO,
                    message="Condition not met and 'else' assertion passed.",
                    target="",
                )
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message="Condition not met and 'else' assertion failed.",
                target="",
            )


class OneOf(BaseAssertionGroup):
    """Exactly one assertion must pass (XOR)."""

    model_config = ConfigDict(frozen=True)
    check: Literal["one_of"] = "one_of"  # type: ignore[assignment]

    def evaluate(self, file: File) -> ValidationResult:
        passing_count = sum(1 for assertion in self.assertions if assertion.evaluate(file).valid)
        if passing_count == 1:
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.INFO,
                message="Exactly one assertion passed in 'one_of'.",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=Severity.ERROR,
            message=f"Expected exactly 1 assertion to pass in 'one_of', but {passing_count} passed.",
            target="",
        )


class AtLeast(BaseAssertionGroup):
    """At least N assertions must pass."""

    model_config = ConfigDict(frozen=True)
    check: Literal["at_least"] = "at_least"  # type: ignore[assignment]
    count: int

    def evaluate(self, file: File) -> ValidationResult:
        passing_count = sum(1 for assertion in self.assertions if assertion.evaluate(file).valid)
        if passing_count >= self.count:
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.INFO,
                message=f"At least {self.count} assertions passed ({passing_count} passed).",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=Severity.ERROR,
            message=f"Expected at least {self.count} assertions to pass, but only {passing_count} passed.",
            target="",
        )


class AtMost(BaseAssertionGroup):
    """At most N assertions can pass."""

    model_config = ConfigDict(frozen=True)
    check: Literal["at_most"] = "at_most"  # type: ignore[assignment]
    count: int

    def evaluate(self, file: File) -> ValidationResult:
        passing_count = sum(1 for assertion in self.assertions if assertion.evaluate(file).valid)
        if passing_count <= self.count:
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.INFO,
                message=f"At most {self.count} assertions passed ({passing_count} passed).",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=Severity.ERROR,
            message=f"Expected at most {self.count} assertions to pass, but {passing_count} passed.",
            target="",
        )


class Exactly(BaseAssertionGroup):
    """Exactly N assertions must pass."""

    model_config = ConfigDict(frozen=True)
    check: Literal["exactly"] = "exactly"  # type: ignore[assignment]
    count: int

    def evaluate(self, file: File) -> ValidationResult:
        passing_count = sum(1 for assertion in self.assertions if assertion.evaluate(file).valid)
        if passing_count == self.count:
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.INFO,
                message=f"Exactly {self.count} assertions passed.",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=Severity.ERROR,
            message=f"Expected exactly {self.count} assertions to pass, but {passing_count} passed.",
            target="",
        )
