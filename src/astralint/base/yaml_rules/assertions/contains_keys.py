from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class ContainsKeysAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["contains_keys"] = "contains_keys"  # type: ignore[assignment]
    keys: frozenset[str]

    _default_template: str = "{% if valid %}all required keys present{% else %}missing keys: {{ missing_keys | join(', ') }}{% endif %}"
    _not_dict_template: str = "value is not an object"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        if not isinstance(value, dict):
            ctx = build_context(target, path, value, valid=False, keys=self.keys, **(captures or {}))
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(self._not_dict_template, ctx),
                target=target,
            )
        missing_keys = self.keys - value.keys()
        passed = not missing_keys
        ctx = build_context(
            target,
            path,
            value,
            valid=passed,
            keys=self.keys,
            missing_keys=missing_keys,
            **(captures or {}),
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
