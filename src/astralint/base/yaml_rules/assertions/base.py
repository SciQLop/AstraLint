import re
from typing import Any, Union, Annotated

from pydantic import BaseModel, ConfigDict, Field

from ...file import File
from ...validation_result import ValidationResult, ValidationResultGroup, Severity


def flatten_object(obj: Any) -> list[tuple[str, Any]]:
    """Flatten an object into (path, value) pairs."""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not callable(v):
                results.append((k, v))
                results.extend(
                    [(f"{k}/{sub_k}", sub_v) for sub_k, sub_v in flatten_object(v) if not sub_k.startswith("_")])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if not callable(v):
                results.append((f"{i}", v))
                results.extend(
                    [(f"{i}/{sub_k}", sub_v) for sub_k, sub_v in flatten_object(v) if not sub_k.startswith("_")])
    elif hasattr(obj, "__dict__"):
        for k, v in vars(obj).items():
            if not callable(v):
                results.append((k, v))
                results.extend(
                    [(f"{k}/{sub_k}", sub_v) for sub_k, sub_v in flatten_object(v)
                     if not sub_k.startswith("_")])
    return results


def resolve_path(obj: Any, path: str) -> list[tuple[str, Any]]:
    """Returns matching (path, value) pairs for a '/' separated path with regex support."""
    flattened = flatten_object(obj)
    rx = re.compile("^" + path + "$")
    return list(filter(lambda kv: rx.match(kv[0]), flattened))


_registry: dict[str, type["BaseAssertion"]] = {}


class BaseAssertion(BaseModel):
    model_config = ConfigDict(frozen=True)
    check: str
    path: str
    error_if_no_match: bool = Field(default=True)
    message: str = Field(default="")

    def __init_subclass__(cls):
        super().__init_subclass__()
        if hasattr(cls, "check"):
            if cls.check in _registry:
                raise ValueError(f"Duplicate assertion check: {cls.check}")
            _registry[cls.check] = cls

    def evaluate(self, file: File) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        results: list[ValidationResult] = []
        if not matches:
            if self.error_if_no_match:
                return ValidationResult(valid=False, reference="", severity=Severity.ERROR,
                                        message=f"Path '{self.path}' did not match any values.", target=self.path)
            else:
                return ValidationResult(valid=True, reference="", severity=Severity.INFO,
                                        message=f"Path '{self.path}' did not match any values, but that's okay.",
                                        target=self.path)
        for path, value in matches:
            result = self.single_assertion(file, path, value)
            results.append(result)
        return ValidationResultGroup(
            name=self.__class__.__name__,
            rule_reference="",
            results=results,
            severity=Severity.INFO,
        )

    def single_assertion(self, file: File, path: str, value: Any) -> ValidationResult:
        ...


def get_assertion_union():
    """Build discriminated union from registered types."""
    types = tuple(list(_registry.values()))
    return Annotated[Union[types], Field(discriminator="check")]
