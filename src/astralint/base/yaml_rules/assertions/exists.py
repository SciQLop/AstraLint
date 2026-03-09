from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, clean_target, render_message, resolve_path_with_captures


class ExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["exists"] = "exists"  # type: ignore[assignment]

    _default_template: str = "{% if valid %}{{ target or path }} exists{% else %}{{ target or path }} does not exist{% endif %}"

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path_with_captures(file, self.path)
        target = clean_target(self.path)
        passed = bool(matches)
        captures = matches[0][2] if matches else {}
        ctx = {"target": target, "path": self.path, "valid": passed, **captures}
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )


class NotExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_exists"] = "not_exists"  # type: ignore[assignment]

    _default_template: str = "{% if valid %}{{ target or path }} does not exist as expected{% else %}{{ target or path }} exists but should not{% endif %}"

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path_with_captures(file, self.path)
        target = clean_target(self.path)
        passed = not bool(matches)
        captures = matches[0][2] if matches else {}
        ctx = {"target": target, "path": self.path, "valid": passed, **captures}
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
