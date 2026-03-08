from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup
from .base import BaseAssertion, clean_target, render_message, resolve_path


class ExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["exists"] = "exists"  # type: ignore[assignment]

    _default_pass_template: str = "{{ target or path }} exists"
    _default_fail_template: str = "{{ target or path }} does not exist"

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        target = clean_target(self.path)
        ctx = {"target": target, "path": self.path}
        if matches:
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_pass_template, ctx),
                target=target,
            )
        else:
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_fail_template, ctx),
                target=target,
            )


class NotExistsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_exists"] = "not_exists"  # type: ignore[assignment]

    _default_pass_template: str = "{{ target or path }} does not exist as expected"
    _default_fail_template: str = "{{ target or path }} exists but should not"

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        target = clean_target(self.path)
        ctx = {"target": target, "path": self.path}
        if matches:
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
                severity=severity,
                message=render_message(self.message or self._default_pass_template, ctx),
                target=target,
            )
