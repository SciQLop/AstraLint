from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class IsTrueAssertion(BaseAssertion):
    """A boolean value must be True.

    False fails; None is treated as not applicable and passes (e.g. a codec that
    does not expose the flag). Used for structural facts like a variable being a
    zVariable or its records being contiguous.
    """

    model_config = ConfigDict(frozen=True)
    check: Literal["is_true"] = "is_true"  # type: ignore[assignment]

    _default_template: str = (
        "{% if valid %}condition holds{% else %}condition does not hold{% endif %}"
    )

    def single_assertion(
        self,
        file: File,
        path: str,
        value: object,
        severity: Severity,
        captures: dict[str, str] | None = None,
    ) -> ValidationResult:
        target = clean_target(path)

        if value is None:
            return ValidationResult(
                valid=True, reference="", severity=severity, message="", target=target
            )

        passed = value is True
        ctx = build_context(target, path, value, valid=passed, **(captures or {}))
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
