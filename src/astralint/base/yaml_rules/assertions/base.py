import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from ...file import File
from ...validation_result import ValidationResult


def flatten_object(obj: Any) -> list[tuple[str, Any]]:
    """Flatten an object into (path, value) pairs."""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not callable(v):
                results.append((k, v))
                results.extend([(f"{k}/{sub_k}", sub_v) for sub_k, sub_v in flatten_object(v)])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if not callable(v):
                results.append((f"[{i}]", v))
                results.extend([(f"[{i}]/{sub_k}", sub_v) for sub_k, sub_v in flatten_object(v)])
    elif hasattr(obj, "__dict__"):
        for k, v in vars(obj).items():
            if not callable(v):
                results.append((k, v))
                results.extend([(f"{k}/{sub_k}", sub_v) for sub_k, sub_v in flatten_object(v)])
    return results


def resolve_path(obj: Any, path: str) -> list[tuple[str, Any]]:
    """Returns matching (path, value) pairs for a '/' separated path with regex support."""
    flattened = flatten_object(obj)
    rx = re.compile("^" + path + "$")
    return list(filter(lambda kv: rx.match(kv[0]), flattened))


class BaseAssertion(BaseModel):
    model_config = ConfigDict(frozen=True)
    check: str
    path: str
    message: str

    def evaluate(self, file: File) -> ValidationResult:
        ...
