from typing import Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


def _parse(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _at_least(value: tuple[int, ...], minimum: tuple[int, ...]) -> bool:
    length = max(len(value), len(minimum))
    pad = lambda v: v + (0,) * (length - len(v))  # noqa: E731
    return pad(value) >= pad(minimum)


class VersionAtLeastAssertion(BaseAssertion):
    """A dotted version string (major.minor.patch) must be >= a minimum.

    Compares numerically per component (so '3.10' > '3.9'), unlike a regex or a
    lexicographic string comparison. A None/absent value is treated as not
    applicable and passes (e.g. a codec that exposes no version).
    """

    model_config = ConfigDict(frozen=True)
    check: Literal["version_at_least"] = "version_at_least"  # type: ignore[assignment]
    minimum: str

    _default_template: str = "{% if valid %}version {{ value }} is at least {{ minimum }}{% else %}version {{ value }} is older than the required minimum {{ minimum }}{% endif %}"
    _unparseable_template: str = "could not parse version {{ value }}"

    def single_assertion(
        self,
        file: File,
        path: str,
        value: object,
        severity: Severity,
        captures: dict[str, str] | None = None,
    ) -> ValidationResult:
        target = clean_target(path)
        extra = {"minimum": self.minimum, **(captures or {})}

        if value is None:
            return ValidationResult(
                valid=True, reference="", severity=severity, message="", target=target
            )

        try:
            passed = _at_least(_parse(str(value)), _parse(self.minimum))
            template = self.message or self._default_template
        except ValueError:
            passed = False
            template = self._unparseable_template

        ctx = build_context(target, path, value, valid=passed, **extra)
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )
