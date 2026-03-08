import re
from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class MatchesAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["matches"] = "matches"  # type: ignore[assignment]
    pattern: re.Pattern

    _default_template: str = "{% if valid %}'{{ value }}' matches pattern '{{ pattern }}'{% else %}'{{ value }}' does not match pattern '{{ pattern }}'{% endif %}"
    _not_string_template: str = "expected a string value, got {{ value.__class__.__name__ }}"

    def single_assertion(
        self, file: File, path: str, value: str, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)

        if not isinstance(value, str):
            ctx = build_context(target, path, value, valid=False, pattern=self.pattern.pattern)
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self._not_string_template, ctx),
                target=target,
            )

        passed = bool(re.match(self.pattern, value))
        ctx = build_context(target, path, value, valid=passed, pattern=self.pattern.pattern)
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
