"""Configuration schema for AstraLint."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


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
    severity_overrides: dict[str, str] = Field(default_factory=dict)

    # Custom rule paths (load additional YAML rules)
    extra_rules: list[Path] = Field(default_factory=list)

    # File patterns for linting
    include: list[str] = Field(default_factory=lambda: ["**/*.cdf"])
    exclude: list[str] = Field(default_factory=list)

    # Output settings
    output: OutputConfig = Field(default_factory=OutputConfig)

    model_config = {"extra": "forbid"}  # Raise error on unknown fields

