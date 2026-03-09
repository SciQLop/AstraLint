from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class ContainsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["in"] = "in"  # type: ignore[assignment]
    values: list[Any]

    _default_template: str = "{% if valid %}'{{ value }}' is in the expected values{% else %}'{{ value }}' is not in the expected values{% endif %}"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        passed = value in self.values
        ctx = build_context(target, path, value, valid=passed, values=self.values, **(captures or {}))
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )


class NotContainsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_in"] = "not_in"  # type: ignore[assignment]
    values: list[Any]

    _default_template: str = "{% if valid %}'{{ value }}' is not in the disallowed values{% else %}'{{ value }}' is in the disallowed values{% endif %}"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        passed = value not in self.values
        ctx = build_context(target, path, value, valid=passed, values=self.values, **(captures or {}))
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )


class LengthAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["length"] = "length"  # type: ignore[assignment]
    min: int | None = None
    max: int | None = None
    value: int | None = None

    _default_template: str = "{% if valid %}length {{ length }} is within expected bounds{% else %}{% if expected is not none %}length {{ length }}, expected {{ expected }}{% elif min is not none and length < min %}length {{ length }} is less than minimum {{ min }}{% elif max is not none and length > max %}length {{ length }} exceeds maximum {{ max }}{% endif %}{% endif %}"
    _no_length_template: str = "value does not have a length"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        try:
            length = len(value)
            passed = True
            if self.value is not None:
                passed = length == self.value
            elif self.min is not None and length < self.min:
                passed = False
            elif self.max is not None and length > self.max:
                passed = False
            ctx = build_context(
                target,
                path,
                value,
                valid=passed,
                length=length,
                min=self.min,
                max=self.max,
                expected=self.value,
                **(captures or {}),
            )
            return ValidationResult(
                valid=passed,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_template, ctx),
                target=target,
            )
        except TypeError:
            ctx = build_context(target, path, value, valid=False, **(captures or {}))
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self.message or self._no_length_template, ctx),
                target=target,
            )


class NotEmptyAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_empty"] = "not_empty"  # type: ignore[assignment]

    _default_template: str = "{% if valid %}{{ attribute or variable or path }} is not empty{% else %}{{ attribute or variable or path }} is empty{% endif %}"
    _no_length_template: str = "value does not have a length"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        try:
            passed = len(value) > 0
            ctx = build_context(target, path, value, valid=passed, **(captures or {}))
            return ValidationResult(
                valid=passed,
                reference="",
                severity=severity,
                message=render_message(self.message or self._default_template, ctx),
                target=target,
            )
        except TypeError:
            ctx = build_context(target, path, value, valid=False, **(captures or {}))
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self.message or self._no_length_template, ctx),
                target=target,
            )


class RequiresAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["requires"] = "requires"  # type: ignore[assignment]
    key: str

    _default_template: str = "{% if valid %}required key '{{ key }}' present{% else %}missing required key '{{ key }}'{% endif %}"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        passed = self.key in value
        ctx = build_context(target, path, value, valid=passed, key=self.key, **(captures or {}))
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )


class ArrayShapeAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["array_shape"] = "array_shape"  # type: ignore[assignment]
    shape: list[int]

    _default_template: str = "shape matches expected {{ expected_shape }}"
    _not_array_template: str = "value is not an array"
    _dim_mismatch_template: str = "has {{ actual_dims }} dimensions, expected {{ expected_dims }}"
    _item_mismatch_template: str = (
        "item {{ index }} has length {{ actual_length }}, expected {{ expected_length }}"
    )

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity, captures: dict[str, str] | None = None
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, valid=False, expected_shape=self.shape, **(captures or {}))
        if not isinstance(value, list):
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(self.message or self._not_array_template, ctx),
                target=target,
            )
        if len(value) != len(self.shape):
            ctx["actual_dims"] = len(value)
            ctx["expected_dims"] = len(self.shape)
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(self.message or self._dim_mismatch_template, ctx),
                target=target,
            )
        for i, (item, expected_length) in enumerate(zip(value, self.shape, strict=True)):
            if not isinstance(item, list) or len(item) != expected_length:
                ctx["index"] = i
                ctx["actual_length"] = len(item) if isinstance(item, list) else 0
                ctx["expected_length"] = expected_length
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message=render_message(self.message or self._item_mismatch_template, ctx),
                    target=target,
                )
        ctx["valid"] = True
        return ValidationResult(
            valid=True,
            reference="",
            severity=severity,
            message=render_message(self.message or self._default_template, ctx),
            target=target,
        )
