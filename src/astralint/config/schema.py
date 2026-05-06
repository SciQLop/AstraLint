"""Configuration schema for AstraLint."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..base.validation_result import Severity

_OVERRIDABLE_SEVERITIES = {Severity.ERROR, Severity.WARNING, Severity.INFO}


class OutputConfig(BaseModel):
    """Output configuration settings."""

    format: Literal["console", "html", "json"] = "console"
    verbose: bool = False
    show_passed: bool = True
    dest: Path | None = None


class AstraLintConfig(BaseModel):
    """Main configuration schema for AstraLint.

    This defines all configuration options that can be set via:
    - pyproject.toml [tool.astralint]
    - .astralint.yaml
    - CLI arguments
    """

    # Default suite to use
    suite: str = "ISTP"

    # Rule filtering (supports regex patterns)
    select: list[str] = Field(default_factory=list)
    ignore: list[str] = Field(default_factory=list)

    # Severity overrides (rule_reference -> new_severity)
    severity_overrides: dict[str, Severity] = Field(default_factory=dict)

    @field_validator("severity_overrides")
    @classmethod
    def _validate_severities(cls, v: dict[str, Severity]) -> dict[str, Severity]:
        for ref, sev in v.items():
            if sev not in _OVERRIDABLE_SEVERITIES:
                raise ValueError(
                    f"severity_overrides[{ref!r}]: {sev.value!r} is not an overridable "
                    f"severity (allowed: ERROR, WARNING, INFO)"
                )
        return v

    # Custom rule paths (load additional YAML rules)
    extra_rules: list[Path] = Field(default_factory=list)

    # File patterns for linting
    include: list[str] = Field(default_factory=lambda: ["**/*.cdf"])
    exclude: list[str] = Field(default_factory=list)

    # Output settings
    output: OutputConfig = Field(default_factory=OutputConfig)

    model_config = {"extra": "forbid"}  # Raise error on unknown fields
