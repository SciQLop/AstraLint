import re
from typing import Annotated, Any, Union

from jinja2 import Environment
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...file import File
from ...validation_result import Severity, ValidationResult, ValidationResultGroup

_jinja_env = Environment()

_TARGET_PATTERN = re.compile(
    r"^variables/(?P<var>[^/]+)/attributes/(?P<attr>[^/]+)"
    r"|^variables/(?P<var_only>[^/]+)"
    r"|^attributes/(?P<attr_only>[^/]+)"
)


def render_message(template: str, context: dict) -> str:
    return _jinja_env.from_string(template).render(context)


def clean_target(raw_path: str) -> str:
    m = _TARGET_PATTERN.search(raw_path)
    if not m:
        return ""
    if m.group("var") and m.group("attr"):
        var = m.group("var")
        attr = m.group("attr")
        return f"{var}/{attr}" if var != ".*" else attr
    if m.group("var_only"):
        var = m.group("var_only")
        return "" if var == ".*" else var
    if m.group("attr_only"):
        return m.group("attr_only")
    return ""


def flatten_object(obj: Any) -> list[tuple[str, Any]]:
    """Flatten an object into (path, value) pairs."""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not callable(v):
                results.append((k, v))
                results.extend(
                    [
                        (f"{k}/{sub_k}", sub_v)
                        for sub_k, sub_v in flatten_object(v)
                        if not sub_k.startswith("_")
                    ]
                )
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if not callable(v):
                results.append((f"{i}", v))
                results.extend(
                    [
                        (f"{i}/{sub_k}", sub_v)
                        for sub_k, sub_v in flatten_object(v)
                        if not sub_k.startswith("_")
                    ]
                )
    elif hasattr(obj, "__dict__"):
        for k, v in vars(obj).items():
            if not callable(v):
                results.append((k, v))
                results.extend(
                    [
                        (f"{k}/{sub_k}", sub_v)
                        for sub_k, sub_v in flatten_object(v)
                        if not sub_k.startswith("_")
                    ]
                )
    return results


def resolve_path(obj: Any, path: str) -> list[tuple[str, Any]]:
    """Returns matching (path, value) pairs for a '/' separated path with regex support."""
    flattened = flatten_object(obj)
    rx = re.compile("^" + path + "$")
    return list(filter(lambda kv: rx.match(kv[0]), flattened))


_CAPTURE_RE = re.compile(r"\{(\w+)(?::([^}]+))?\}")


def parse_captures(path: str) -> tuple[str, dict[str, int]]:
    """Parse {name} and {name:pattern} captures from a path into a regex pattern and capture map."""
    captures: dict[str, int] = {}
    group_index = 0

    def _replace(match: re.Match) -> str:
        nonlocal group_index
        name = match.group(1)
        pattern = match.group(2) or "[^/]*"
        captures[name] = group_index
        group_index += 1
        return f"({pattern})"

    regex_pattern = _CAPTURE_RE.sub(_replace, path)
    return regex_pattern, captures


def resolve_path_with_captures(
    obj: Any, path: str
) -> list[tuple[str, Any, dict[str, str]]]:
    """Like resolve_path but extracts captured values from {name} placeholders."""
    pattern, captures = parse_captures(path)
    flattened = flatten_object(obj)
    rx = re.compile("^" + pattern + "$")
    results: list[tuple[str, Any, dict[str, str]]] = []
    for flat_path, value in flattened:
        m = rx.match(flat_path)
        if m:
            captured = {name: m.group(idx + 1) for name, idx in captures.items()}
            results.append((flat_path, value, captured))
    return results


def interpolate_captures(template: str, captures: dict[str, str]) -> str:
    """Replace {name} placeholders in template with values from captures dict."""
    result = template
    for name, value in captures.items():
        result = result.replace(f"{{{name}}}", value)
    return result


_registry: dict[str, type["BaseEvaluable"]] = {}


class BaseEvaluable(BaseModel):
    model_config = ConfigDict(frozen=True)
    check: str

    def __init_subclass__(cls):
        super().__init_subclass__()
        if hasattr(cls, "check"):
            if cls.check in _registry:
                raise ValueError(f"Duplicate check: {cls.check}")
            _registry[cls.check] = cls

    def evaluate(
        self, file: File, severity: Severity
    ) -> ValidationResult | ValidationResultGroup: ...


class BaseAssertion(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    path: str
    error_if_no_match: bool = Field(default=True)
    message: str = Field(default="")

    def evaluate(self, file: File, severity: Severity) -> ValidationResult | ValidationResultGroup:
        matches = resolve_path(file, self.path)
        results: list[ValidationResult | ValidationResultGroup] = []
        if not matches:
            if self.error_if_no_match:
                return ValidationResult(
                    valid=False,
                    reference="",
                    severity=Severity.ERROR,
                    message=f"Path '{self.path}' did not match any values.",
                    target=self.path,
                )
            else:
                return ValidationResult(
                    valid=True,
                    reference="",
                    severity=Severity.INFO,
                    message=f"Path '{self.path}' did not match any values, but that's okay.",
                    target=self.path,
                )
        for path, value in matches:
            result = self.single_assertion(file, path, value, severity=severity)
            results.append(result)
        return ValidationResultGroup(
            name=self.__class__.__name__,
            rule_reference="",
            results=results,
            severity=severity,
        )

    def single_assertion(
        self, file: File, path: str, value: Any, severity: Severity
    ) -> ValidationResult: ...


class BaseAssertionGroup(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    assertions: list[Any]

    @model_validator(mode="before")
    @classmethod
    def parse_assertions(cls, data: dict) -> dict:
        """Parse assertions using the discriminated union."""
        assertion = get_assertion_union()
        from pydantic import TypeAdapter

        adapter = TypeAdapter(list[assertion])
        data["assertions"] = adapter.validate_python(data.get("assertions", []))
        return data


def get_assertion_union():
    """Build discriminated union from registered types."""
    types = tuple(list(_registry.values()))
    return Annotated[Union[types], Field(discriminator="check")]  # noqa: UP007
