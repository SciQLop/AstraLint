from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from ... import ValidationResultGroup
from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertionGroup, BaseEvaluable, get_assertion_union


class AllOf(BaseAssertionGroup):
    model_config = ConfigDict(frozen=True)
    check: Literal["all_of"] = "all_of"  # type: ignore[assignment]

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file, severity)
            if not result.valid:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message="Assertion failed in 'all_of'",
                    target="",
                )
        return ValidationResult(
            valid=True,
            reference="",
            severity=severity,
            message="All assertions in 'all_of' passed successfully.",
            target="",
        )


class AnyOf(BaseAssertionGroup):
    model_config = ConfigDict(frozen=True)
    check: Literal["any_of"] = "any_of"  # type: ignore[assignment]

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file, severity)
            if result.valid:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=severity,
                    message="At least one assertion in 'any_of' passed successfully.",
                    target="",
                )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message="All assertions in 'any_of' failed.",
            target="",
        )


class NoneOf(BaseAssertionGroup):
    model_config = ConfigDict(frozen=True)
    check: Literal["none_of"] = "none_of"  # type: ignore[assignment]

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        for assertion in self.assertions:
            result = assertion.evaluate(file, severity)
            if result.valid:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message="At least one assertion in 'none_of' passed, which is not expected",
                    target="",
                )
        return ValidationResult(
            valid=True,
            reference="",
            severity=severity,
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

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        result = self.assertion.evaluate(file, severity)
        if result.valid:
            return ValidationResult(
                valid=False,
                reference="",
                message=f"Assertion '{result}' passed, but was expected to fail in 'not'.",
                target="",
                severity=severity,
            )
        return ValidationResult(
            valid=True,
            reference="",
            message=f"Assertion '{result}' failed as expected in 'not'.",
            target="",
            severity=severity,
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

    def evaluate(self, file: File, severity: Severity) -> ValidationResultGroup | ValidationResult:
        condition_result = self.if_.evaluate(file, severity)
        if not condition_result.valid:
            return ValidationResult(
                valid=True,
                reference="",
                severity=Severity.SKIPPED,
                message="Condition not met, assertion skipped.",
                target="",
            )
        return ValidationResultGroup(
            name="IfThen",
            rule_reference="",
            results=[self.then.evaluate(file, severity)],
            severity=severity,
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

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        condition_result = self.if_.evaluate(file, severity)
        if condition_result.valid:
            then_result = self.then.evaluate(file, severity)
            return ValidationResultGroup(
                name="IfThenElse (Then branch)",
                rule_reference="",
                results=[then_result],
                severity=severity,
            )
        else:
            else_result = self.else_.evaluate(file, severity)
            return ValidationResultGroup(
                name="IfThenElse (Else branch)",
                rule_reference="",
                results=[else_result],
                severity=severity,
            )


class OneOf(BaseAssertionGroup):
    """Exactly one assertion must pass (XOR)."""

    model_config = ConfigDict(frozen=True)
    check: Literal["one_of"] = "one_of"  # type: ignore[assignment]

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        passing_count = sum(
            1 for assertion in self.assertions if assertion.evaluate(file, severity).valid
        )
        if passing_count == 1:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message="Exactly one assertion passed in 'one_of'.",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=f"Expected exactly 1 assertion to pass in 'one_of', but {passing_count} passed.",
            target="",
        )


class AtLeast(BaseAssertionGroup):
    """At least N assertions must pass."""

    model_config = ConfigDict(frozen=True)
    check: Literal["at_least"] = "at_least"  # type: ignore[assignment]
    count: int

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        passing_count = sum(
            1 for assertion in self.assertions if assertion.evaluate(file, severity).valid
        )
        if passing_count >= self.count:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=f"At least {self.count} assertions passed ({passing_count} passed).",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=f"Expected at least {self.count} assertions to pass, but only {passing_count} passed.",
            target="",
        )


class AtMost(BaseAssertionGroup):
    """At most N assertions can pass."""

    model_config = ConfigDict(frozen=True)
    check: Literal["at_most"] = "at_most"  # type: ignore[assignment]
    count: int

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        passing_count = sum(
            1 for assertion in self.assertions if assertion.evaluate(file, severity).valid
        )
        if passing_count <= self.count:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=f"At most {self.count} assertions passed ({passing_count} passed).",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=f"Expected at most {self.count} assertions to pass, but {passing_count} passed.",
            target="",
        )


class Exactly(BaseAssertionGroup):
    """Exactly N assertions must pass."""

    model_config = ConfigDict(frozen=True)
    check: Literal["exactly"] = "exactly"  # type: ignore[assignment]
    count: int

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        passing_count = sum(
            1 for assertion in self.assertions if assertion.evaluate(file, severity).valid
        )
        if passing_count == self.count:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=f"Exactly {self.count} assertions passed.",
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=f"Expected exactly {self.count} assertions to pass, but {passing_count} passed.",
            target="",
        )
