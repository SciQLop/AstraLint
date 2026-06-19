import re
from typing import Annotated, Any, Union

from jinja2 import Environment, TemplateError
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
    try:
        return _jinja_env.from_string(template).render(context)
    except TemplateError as e:
        return f"[template error: {e}] template: {template}"


def build_context(target: str, raw_path: str, value: Any, **extra: Any) -> dict:
    ctx: dict = {"value": value, "path": raw_path, "variable": None, "attribute": None}
    parts = target.split("/")
    if len(parts) == 2:
        ctx["variable"], ctx["attribute"] = parts
    elif len(parts) == 1 and target:
        ctx["attribute"] = target if raw_path.startswith("attributes/") else None
        ctx["variable"] = target if raw_path.startswith("variables/") else None
    ctx.update(extra)
    return ctx


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


import weakref

# Cache for flatten_object keyed on id(obj). A weakref.finalize on each cached
# object ensures its entry is removed before its id can be reused, so id()
# collisions never return stale data. Objects that can't hold weak references
# (e.g., dicts, lists) are simply not cached.
_FLATTEN_CACHE: dict[int, list[tuple[str, Any]]] = {}


def clear_flatten_cache() -> None:
    _FLATTEN_CACHE.clear()


def flatten_object(obj: Any) -> list[tuple[str, Any]]:
    """Flatten an object into (path, value) pairs."""
    key = id(obj)
    cached = _FLATTEN_CACHE.get(key)
    if cached is not None:
        return cached

    results: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        items = obj.items()
    elif isinstance(obj, list):
        items = enumerate(obj)
    elif hasattr(obj, "__dict__"):
        items = vars(obj).items()
    else:
        return results

    for k, v in items:
        if callable(v):
            continue
        path_key = str(k)
        results.append((path_key, v))
        results.extend(
            (f"{path_key}/{sub_k}", sub_v)
            for sub_k, sub_v in flatten_object(v)
            if not sub_k.startswith("_")
        )

    try:
        weakref.finalize(obj, _FLATTEN_CACHE.pop, key, None)
        _FLATTEN_CACHE[key] = results
    except TypeError:
        pass  # Not weakref-able — skip caching for this object.
    return results


def resolve_path(obj: Any, path: str) -> list[tuple[str, Any]]:
    """Returns matching (path, value) pairs for a '/' separated path with regex support."""
    flattened = flatten_object(obj)
    rx = re.compile("^" + path + "$")
    return list(filter(lambda kv: rx.match(kv[0]), flattened))


_CAPTURE_RE = re.compile(r"\{(\w+)(?::([^}]+))?\}")


def parse_captures(path: str) -> tuple[str, list[str]]:
    """Parse {name} and {name:pattern} captures from a path into a regex pattern and capture names."""
    capture_names: list[str] = []

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        if name in capture_names:
            raise ValueError(f"Duplicate capture name: '{name}'")
        pattern = match.group(2) or "[^/]*"
        capture_names.append(name)
        return f"(?P<{name}>{pattern})"

    regex_pattern = _CAPTURE_RE.sub(_replace, path)
    return regex_pattern, capture_names


def resolve_path_with_captures(obj: Any, path: str) -> list[tuple[str, Any, dict[str, str]]]:
    """Like resolve_path but extracts captured values from {name} placeholders."""
    pattern, capture_names = parse_captures(path)
    flattened = flatten_object(obj)
    rx = re.compile("^" + pattern + "$")
    results: list[tuple[str, Any, dict[str, str]]] = []
    for flat_path, value in flattened:
        m = rx.match(flat_path)
        if m:
            captured = {name: m.group(name) for name in capture_names}
            results.append((flat_path, value, captured))
    return results


def interpolate_captures(template: str, captures: dict[str, str]) -> str:
    """Replace {name} placeholders in template with values from captures dict."""
    result = template
    for name, value in captures.items():
        result = result.replace(f"{{{name}}}", value)
    return result


_NO_MATCH_TEMPLATE = "{% if valid %}{{ target or path }} did not match any values (not required){% else %}{{ target or path }} did not match any values{% endif %}"

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
        matches = resolve_path_with_captures(file, self.path)
        results: list[ValidationResult | ValidationResultGroup] = []
        if not matches:
            target = clean_target(self.path)
            valid = not self.error_if_no_match
            ctx = {"target": target, "path": self.path, "valid": valid}
            return ValidationResult(
                valid=valid,
                reference="",
                severity=Severity.ERROR if not valid else Severity.INFO,
                message=render_message(_NO_MATCH_TEMPLATE, ctx),
                target=target,
            )
        for path, value, captures in matches:
            result = self.single_assertion(file, path, value, severity=severity, captures=captures)
            # Surface the actual checked value for display, for scalar checks only
            # (skip dicts/lists like contains_keys targets).
            if isinstance(value, (str, int, float, bool)) and not result.value:
                result = result.model_copy(update={"value": str(value)})
            results.append(result)
        return ValidationResultGroup(
            name=self.__class__.__name__,
            rule_reference="",
            results=results,
            severity=severity,
        )

    def single_assertion(
        self,
        file: File,
        path: str,
        value: Any,
        severity: Severity,
        captures: dict[str, str] | None = None,
    ) -> ValidationResult: ...


class BaseAssertionGroup(BaseEvaluable):
    model_config = ConfigDict(frozen=True)
    assertions: list[Any]
    message: str = Field(default="")

    def _result_message(self, valid: bool, default: str) -> str:
        if self.message:
            return render_message(self.message, {"valid": valid})
        return default

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
