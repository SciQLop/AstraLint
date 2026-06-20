from collections.abc import Callable
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Scope(str, Enum):  # noqa: UP042
    VARIABLE = "variable"
    GLOBAL = "global"


class ReferenceSource(str, Enum):  # noqa: UP042
    TYPE_RULE = "type_rule"
    GRAPH_RULE = "graph_rule"
    FILENAME = "filename_convention"
    FORMAT_RULE = "format_rule"  # deterministic reshaping of an existing value (length/format)
    USER = "user"


class ApplyPolicy(str, Enum):  # noqa: UP042
    ALWAYS = "always"
    IF_UNIQUE = "if_unique"
    NEVER = "never"


class ResolverOutput(BaseModel):
    """What a resolver function returns (or None when it cannot resolve)."""

    value: Any
    confidence: float | None = None  # overrides entry.confidence_default when set
    provenance_note: str
    ambiguous: bool = False  # for if_unique: stage instead of auto-apply when True
    alternatives: list[Any] = Field(default_factory=list)  # candidate values when ambiguous


class ResolverEntry(BaseModel):
    """One declarative registry row. `resolver` is a direct function reference."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    attribute: str
    scope: Scope
    sources: list[ReferenceSource]
    resolver: Callable
    auto_apply: ApplyPolicy
    confidence_default: float
    triggers: list[str] = Field(
        default_factory=list
    )  # rule references this entry handles; empty = any


class Fix(BaseModel):
    """The auditable unit applied to a CDF."""

    target_path: str  # e.g. "variables/Epoch/attributes/FILLVAL"
    variable: str | None
    attribute: str
    scope: Scope
    action: Literal["add", "set"]  # add = missing attr; set = present-but-wrong
    value: Any
    source: ReferenceSource
    confidence: float
    provenance_note: str
    auto: bool  # decided by the engine: always | (if_unique & not ambiguous)

    @property
    def disposition(self) -> str:
        """How the fix is offered: applied automatically, suggested for review,
        or flagged as requiring human input (a value-less USER fix)."""
        if self.auto:
            return "auto"
        if self.source == ReferenceSource.USER:
            return "user"
        return "staged"
