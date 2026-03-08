import re
from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, clean_target, render_message


class MatchesAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["matches"] = "matches"  # type: ignore[assignment]
    pattern: re.Pattern

    _default_pass_template: str = "'{{ value }}' matches pattern '{{ pattern }}'"
    _default_fail_template: str = "'{{ value }}' does not match pattern '{{ pattern }}'"
    _not_string_template: str = "expected a string value, got {{ value.__class__.__name__ }}"

    def single_assertion(
        self, file: File, path: str, value: str, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = {
            "value": value,
            "pattern": self.pattern.pattern,
            "variable": None,
            "attribute": None,
            "path": path,
        }
        parts = target.split("/")
        if len(parts) == 2:
            ctx["variable"], ctx["attribute"] = parts
        elif len(parts) == 1 and target:
            ctx["attribute"] = target if path.startswith("attributes/") else None
            ctx["variable"] = target if path.startswith("variables/") else None

        if not isinstance(value, str):
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self._not_string_template, ctx),
                target=target,
            )
        elif not re.match(self.pattern, value):
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_fail_template, ctx),
                target=target,
            )
        else:
            return ValidationResult(
                valid=True,
                reference="",
                message=render_message(self.message or self._default_pass_template, ctx),
                severity=severity,
                target=target,
            )
