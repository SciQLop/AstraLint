from typing import Literal

from pydantic import ConfigDict, Field

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import (
    BaseEvaluable,
    clean_target,
    interpolate_captures,
    render_message,
    resolve_path,
    resolve_path_with_captures,
    unwrap_scalar,
)

_operators = {
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}

_NO_MATCH_TEMPLATE = "{% if valid %}{{ target or path }} did not match any values (not required){% else %}{{ target or path }} did not match any values{% endif %}"


class CompareToAssertion(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    check: Literal["compare_to"] = "compare_to"  # type: ignore[assignment]
    path: str
    operator: Literal["=", "!=", "<", "<=", ">", ">="]
    other_path: str
    error_if_no_match: bool = Field(default=True)
    message: str = Field(default="")

    _default_template: str = "{% if valid %}{{ value }} {{ operator }} {{ other_value }}{% else %}{{ value }} does not satisfy {{ operator }} {{ other_value }}{% endif %}"
    _other_not_found_template: str = "comparison target not found"

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path_with_captures(file, self.path)
        if not matches:
            target = clean_target(self.path)
            valid = not self.error_if_no_match
            ctx = {"target": target, "path": self.path, "valid": valid}
            return ValidationResult(
                valid=valid,
                reference="",
                severity=Severity.ERROR if not valid else Severity.INFO,
                message=render_message(_NO_MATCH_TEMPLATE, ctx),
                target=target,
            )

        results: list[ValidationResult | ValidationResultGroup] = []
        for path, value, captures in matches:
            target = clean_target(path)
            resolved_other = interpolate_captures(self.other_path, captures)
            other_matches = resolve_path(file, resolved_other)

            ctx = {
                "value": value,
                "operator": self.operator,
                "path": path,
                "target": target,
                "variable": None,
                "attribute": None,
                "valid": False,
                **captures,
            }
            parts = target.split("/")
            if len(parts) == 2:
                ctx["variable"], ctx["attribute"] = parts
            elif len(parts) == 1 and target:
                ctx["attribute"] = target if path.startswith("attributes/") else None
                ctx["variable"] = target if path.startswith("variables/") else None

            if not other_matches:
                ctx["other_value"] = None
                results.append(
                    ValidationResult(
                        valid=False,
                        reference="",
                        severity=severity,
                        message=render_message(self.message or self._other_not_found_template, ctx),
                        target=target,
                    )
                )
                continue

            other_value = other_matches[0][1]
            ctx["other_value"] = other_value
            try:
                passed = _operators[self.operator](unwrap_scalar(value), unwrap_scalar(other_value))
            except TypeError:
                passed = False

            ctx["valid"] = passed
            results.append(
                ValidationResult(
                    valid=passed,
                    reference="",
                    severity=severity,
                    message=render_message(self.message or self._default_template, ctx),
                    target=target,
                )
            )

        return ValidationResultGroup(
            name="CompareToAssertion",
            rule_reference="",
            results=results,
            severity=severity,
        )
