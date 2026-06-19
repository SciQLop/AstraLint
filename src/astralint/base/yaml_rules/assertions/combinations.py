from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from ... import ValidationResultGroup
from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import (
    BaseAssertionGroup,
    BaseEvaluable,
    get_assertion_union,
    interpolate_captures,
    parse_captures,
    render_message,
    resolve_path_with_captures,
)


def _path_capture_names(assertion: Any) -> list[str]:
    """Names of {capture} placeholders in an assertion's own ``path`` (if any)."""
    path = getattr(assertion, "path", None)
    if not isinstance(path, str):
        return []
    _, names = parse_captures(path)
    return names


def _concretize(assertion: Any, captures: dict[str, str]) -> Any:
    """Return a copy of an assertion tree with {capture} placeholders interpolated.

    This is what makes ``if_then`` correlate a condition and its requirement on the
    *same* variable: the capture bound by the condition's path (e.g. ``{var}``) is
    substituted into every path of the ``then`` branch.
    """
    if not captures:
        return assertion
    update: dict[str, Any] = {}
    for field in ("path", "other_path", "message"):
        value = getattr(assertion, field, None)
        if isinstance(value, str):
            update[field] = interpolate_captures(value, captures)
    subs = getattr(assertion, "assertions", None)
    if isinstance(subs, list):
        update["assertions"] = [_concretize(a, captures) for a in subs]
    for field in ("assertion", "if_", "then", "else_"):
        child = getattr(assertion, field, None)
        if isinstance(child, BaseEvaluable):
            update[field] = _concretize(child, captures)
    if not update:
        return assertion
    return assertion.model_copy(update=update)


def _distinct_bindings(file: File, if_path: str) -> list[dict[str, str]]:
    bindings: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for _path, _value, captures in resolve_path_with_captures(file, if_path):
        key = tuple(sorted(captures.items()))
        if key not in seen:
            seen.add(key)
            bindings.append(captures)
    return bindings


def _evaluate_per_capture(
    if_: Any,
    then: Any,
    else_: Any | None,
    file: File,
    severity: Severity,
    name: str,
) -> ValidationResult | ValidationResultGroup:
    """Evaluate a conditional once per distinct binding of the condition's path
    captures (e.g. ``{var}``), correlating the requirement with the matched variable."""
    results: list[Any] = []
    for captures in _distinct_bindings(file, if_.path):
        condition = _concretize(if_, captures).evaluate(file, severity)
        if condition.valid:
            results.append(_concretize(then, captures).evaluate(file, severity))
        elif else_ is not None:
            results.append(_concretize(else_, captures).evaluate(file, severity))
    if not results:
        return ValidationResult(
            valid=True,
            reference="",
            severity=Severity.SKIPPED,
            message="Condition not met for any binding, assertion skipped.",
            target="",
        )
    return ValidationResultGroup(name=name, rule_reference="", results=results, severity=severity)


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
                    message=self._result_message(False, "Assertion failed in 'all_of'"),
                    target="",
                )
        return ValidationResult(
            valid=True,
            reference="",
            severity=severity,
            message=self._result_message(True, "All assertions in 'all_of' passed successfully."),
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
                    message=self._result_message(
                        True, "At least one assertion in 'any_of' passed successfully."
                    ),
                    target="",
                )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=self._result_message(False, "All assertions in 'any_of' failed."),
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
                    message=self._result_message(
                        False, "At least one assertion in 'none_of' passed, which is not expected"
                    ),
                    target="",
                )
        return ValidationResult(
            valid=True,
            reference="",
            severity=severity,
            message=self._result_message(True, "All assertions in 'none_of' failed as expected."),
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


class AnyMatch(BaseEvaluable):
    """Existential quantifier over a wrapped assertion's results.

    A wildcard-path assertion (e.g. ``variables/.*/data_type``) normally only
    "passes" when *every* matched value satisfies it. ``any_match`` flips that to
    "passes when *at least one* match satisfies it" — useful for requirements like
    "the dataset contains at least one CDF time (epoch) variable", which must not
    assume a particular variable name."""

    model_config = ConfigDict(frozen=True)
    check: Literal["any_match"] = "any_match"  # type: ignore[assignment]
    assertion: Any
    message: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def parse_assertion(cls, data: dict) -> dict:
        assertion_union = get_assertion_union()
        from pydantic import TypeAdapter

        adapter = TypeAdapter(assertion_union)
        if "assertion" in data:
            data["assertion"] = adapter.validate_python(data["assertion"])
        return data

    def evaluate(self, file: File, severity: Severity) -> ValidationResult:
        # For an existential quantifier, "no matches at all" must be a failure.
        # Neutralize any lenient `error_if_no_match: false` on the wrapped (path)
        # assertion so that an empty match set yields a failing leaf rather than a
        # vacuously-valid one.
        assertion = self.assertion
        if getattr(assertion, "error_if_no_match", None) is False:
            assertion = assertion.model_copy(update={"error_if_no_match": True})
        result = assertion.evaluate(file, severity)
        if isinstance(result, ValidationResultGroup):
            passed = result.count_by_severity()["passed"] > 0
        else:
            passed = result.valid and result.severity != Severity.SKIPPED
        default = (
            "at least one match satisfied the condition"
            if passed
            else "no match satisfied the condition"
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message, {"valid": passed}) if self.message else default,
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

    def evaluate(self, file: File, severity: Severity) -> ValidationResultGroup | ValidationResult:
        if _path_capture_names(self.if_):
            return _evaluate_per_capture(self.if_, self.then, None, file, severity, "IfThen")
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
        if _path_capture_names(self.if_):
            return _evaluate_per_capture(
                self.if_, self.then, self.else_, file, severity, "IfThenElse"
            )
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
                message=self._result_message(True, "Exactly one assertion passed in 'one_of'."),
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=self._result_message(
                False,
                f"Expected exactly 1 assertion to pass in 'one_of', but {passing_count} passed.",
            ),
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
                message=self._result_message(
                    True, f"At least {self.count} assertions passed ({passing_count} passed)."
                ),
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=self._result_message(
                False,
                f"Expected at least {self.count} assertions to pass, but only {passing_count} passed.",
            ),
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
                message=self._result_message(
                    True, f"At most {self.count} assertions passed ({passing_count} passed)."
                ),
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=self._result_message(
                False,
                f"Expected at most {self.count} assertions to pass, but {passing_count} passed.",
            ),
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
                message=self._result_message(True, f"Exactly {self.count} assertions passed."),
                target="",
            )
        return ValidationResult(
            valid=False,
            reference="",
            severity=severity,
            message=self._result_message(
                False,
                f"Expected exactly {self.count} assertions to pass, but {passing_count} passed.",
            ),
            target="",
        )
