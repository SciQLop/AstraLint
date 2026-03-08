from typing import Any, Literal

from pydantic import ConfigDict

from ...file import File
from ...validation_result import Severity, ValidationResult
from .base import BaseAssertion, build_context, clean_target, render_message


class ContainsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["in"] = "in"  # type: ignore[assignment]
    values: list[Any]

    _default_pass_template: str = "'{{ value }}' is in the expected values"
    _default_fail_template: str = "'{{ value }}' is not in the expected values"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, values=self.values)
        passed = value in self.values
        template = self.message or (
            self._default_pass_template if passed else self._default_fail_template
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )


class NotContainsAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_in"] = "not_in"  # type: ignore[assignment]
    values: list[Any]

    _default_pass_template: str = "'{{ value }}' is not in the disallowed values"
    _default_fail_template: str = "'{{ value }}' is in the disallowed values"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, values=self.values)
        passed = value not in self.values
        template = self.message or (
            self._default_pass_template if passed else self._default_fail_template
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )


class LengthAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["length"] = "length"  # type: ignore[assignment]
    min: int | None = None
    max: int | None = None
    value: int | None = None

    _exact_pass_template: str = "length {{ length }} as expected"
    _exact_fail_template: str = "length {{ length }}, expected {{ expected }}"
    _min_fail_template: str = "length {{ length }} is less than minimum {{ min }}"
    _max_fail_template: str = "length {{ length }} exceeds maximum {{ max }}"
    _range_pass_template: str = "length {{ length }} is within expected bounds"
    _no_length_template: str = "value does not have a length"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        try:
            length = len(value)
            ctx = build_context(
                target, path, value, length=length, min=self.min, max=self.max, expected=self.value
            )
            if self.value is not None:
                passed = length == self.value
                template = self.message or (
                    self._exact_pass_template if passed else self._exact_fail_template
                )
                return ValidationResult(
                    valid=passed,
                    reference="",
                    severity=severity,
                    message=render_message(template, ctx),
                    target=target,
                )
            if self.min is not None and length < self.min:
                template = self.message or self._min_fail_template
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message=render_message(template, ctx),
                    target=target,
                )
            if self.max is not None and length > self.max:
                template = self.message or self._max_fail_template
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message=render_message(template, ctx),
                    target=target,
                )
            template = self.message or self._range_pass_template
            return ValidationResult(
                valid=True,
                reference="",
                severity=severity,
                message=render_message(template, ctx),
                target=target,
            )
        except TypeError:
            ctx = build_context(target, path, value)
            template = self.message or self._no_length_template
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(template, ctx),
                target=target,
            )


class NotEmptyAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["not_empty"] = "not_empty"  # type: ignore[assignment]

    _default_pass_template: str = "{{ attribute or variable or path }} is not empty"
    _default_fail_template: str = "{{ attribute or variable or path }} is empty"
    _no_length_template: str = "value does not have a length"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value)
        try:
            passed = len(value) > 0
            template = self.message or (
                self._default_pass_template if passed else self._default_fail_template
            )
            return ValidationResult(
                valid=passed,
                reference="",
                severity=severity,
                message=render_message(template, ctx),
                target=target,
            )
        except TypeError:
            template = self.message or self._no_length_template
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(template, ctx),
                target=target,
            )


class RequiresAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["requires"] = "requires"  # type: ignore[assignment]
    key: str

    _default_pass_template: str = "required key '{{ key }}' present"
    _default_fail_template: str = "missing required key '{{ key }}'"

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, key=self.key)
        passed = self.key in value
        template = self.message or (
            self._default_pass_template if passed else self._default_fail_template
        )
        return ValidationResult(
            valid=passed,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )


class ArrayShapeAssertion(BaseAssertion):
    model_config = ConfigDict(frozen=True)
    check: Literal["array_shape"] = "array_shape"  # type: ignore[assignment]
    shape: list[int]

    _default_pass_template: str = "shape matches expected {{ expected_shape }}"
    _not_array_template: str = "value is not an array"
    _dim_mismatch_template: str = (
        "has {{ actual_dims }} dimensions, expected {{ expected_dims }}"
    )
    _item_mismatch_template: str = (
        "item {{ index }} has length {{ actual_length }}, expected {{ expected_length }}"
    )

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult:
        target = clean_target(path)
        ctx = build_context(target, path, value, expected_shape=self.shape)
        if not isinstance(value, list):
            template = self.message or self._not_array_template
            return ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message=render_message(template, ctx),
                target=target,
            )
        if len(value) != len(self.shape):
            ctx["actual_dims"] = len(value)
            ctx["expected_dims"] = len(self.shape)
            template = self.message or self._dim_mismatch_template
            return ValidationResult(
                valid=False,
                reference="",
                severity=severity,
                message=render_message(template, ctx),
                target=target,
            )
        for i, (item, expected_length) in enumerate(zip(value, self.shape, strict=True)):
            if not isinstance(item, list) or len(item) != expected_length:
                ctx["index"] = i
                ctx["actual_length"] = len(item) if isinstance(item, list) else 0
                ctx["expected_length"] = expected_length
                template = self.message or self._item_mismatch_template
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=severity,
                    message=render_message(template, ctx),
                    target=target,
                )
        template = self.message or self._default_pass_template
        return ValidationResult(
            valid=True,
            reference="",
            severity=severity,
            message=render_message(template, ctx),
            target=target,
        )
