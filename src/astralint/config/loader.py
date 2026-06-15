"""Configuration loading and merging."""

import tomllib
from pathlib import Path

import yaml

from .schema import AstraLintConfig

CONFIG_FILE_NAMES = [".astralint.yaml", ".astralint.yml", "astralint.yaml", "astralint.yml"]

STARTER_CONFIG = """\
# AstraLint Configuration
# Documentation: https://github.com/SciQLop/AstraLint

# Default conformance suite
suite: ISTP

# Rule filtering (use regex patterns)
select: []
  # - "MandatoryGlobalAttributes"
  # - "ISTP-VAR-.*"

ignore: []
  # - "DeprecatedRule"

# Override severity for specific rules
severity_overrides: {}
  # ISTP-VAR-001: WARNING

# Load additional rules from directories
extra_rules: []
  # - "./custom_rules/"

# File patterns
include:
  - "**/*.cdf"

exclude: []
  # - "**/test_data/**"

# Output settings
output:
  format: console  # console | html | json
  verbose: false
  # show_passed: true   # console is quiet (failures only) by default; set true to list passing checks
"""


def find_project_root(start: Path | None = None) -> Path:
    """Walk up directory tree to find project root (pyproject.toml or .git).

    Parameters
    ----------
    start : Path, optional
        Starting directory. Defaults to current working directory.

    Returns
    -------
    Path
        The project root directory.
    """
    path = (start or Path.cwd()).resolve()
    for parent in [path, *path.parents]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return Path.cwd()


def find_config_file(root: Path | None = None) -> Path | None:
    """Find .astralint.yaml or similar config file in project root.

    Parameters
    ----------
    root : Path, optional
        Project root directory. Auto-detected if not provided.

    Returns
    -------
    Path or None
        Path to config file if found, None otherwise.
    """
    root = root or find_project_root()
    for name in CONFIG_FILE_NAMES:
        config_path = root / name
        if config_path.exists():
            return config_path
    return None


def load_pyproject(path: Path) -> dict:
    """Load [tool.astralint] section from pyproject.toml.

    Parameters
    ----------
    path : Path
        Path to pyproject.toml file.

    Returns
    -------
    dict
        Configuration dictionary from [tool.astralint] section.
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("astralint", {})


def load_yaml_config(path: Path) -> dict:
    """Load configuration from YAML file.

    Parameters
    ----------
    path : Path
        Path to YAML config file.

    Returns
    -------
    dict
        Configuration dictionary.
    """
    with open(path) as f:
        return yaml.safe_load(f) or {}


def merge_configs(base: dict, override: dict) -> dict:
    """Deep merge override into base config.

    Parameters
    ----------
    base : dict
        Base configuration.
    override : dict
        Override configuration (takes precedence).

    Returns
    -------
    dict
        Merged configuration.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    project_root: Path | None = None,
    config_file: Path | None = None,
    cli_overrides: dict | None = None,
) -> AstraLintConfig:
    """Load configuration with precedence rules.

    Configuration is loaded and merged in this order (lowest to highest priority):
    1. Built-in defaults
    2. pyproject.toml [tool.astralint]
    3. .astralint.yaml
    4. CLI arguments

    Parameters
    ----------
    project_root : Path, optional
        Project root directory. Auto-detected if not provided.
    config_file : Path, optional
        Explicit config file path. Overrides auto-detection.
    cli_overrides : dict, optional
        CLI argument overrides.

    Returns
    -------
    AstraLintConfig
        Merged configuration object.
    """
    config_data: dict = {}
    root = project_root or find_project_root()

    # Load from pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        config_data = merge_configs(config_data, load_pyproject(pyproject))

    # Load from .astralint.yaml (or explicit config file)
    yaml_config = config_file or find_config_file(root)
    if yaml_config and yaml_config.exists():
        config_data = merge_configs(config_data, load_yaml_config(yaml_config))

    # Apply CLI overrides
    if cli_overrides:
        # Filter out None values
        cli_overrides = {k: v for k, v in cli_overrides.items() if v is not None}
        config_data = merge_configs(config_data, cli_overrides)

    return AstraLintConfig(**config_data)


def validate_config_file(path: Path) -> tuple[bool, str | None]:
    """Validate a configuration file.

    Parameters
    ----------
    path : Path
        Path to configuration file (.yaml, .yml, or .toml).

    Returns
    -------
    tuple[bool, str | None]
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    try:
        if path.suffix == ".toml":
            data = load_pyproject(path)
        else:
            data = load_yaml_config(path)
        AstraLintConfig(**data)
        return True, None
    except Exception as e:
        return False, str(e)


def generate_starter_config() -> str:
    """Generate starter configuration YAML content.

    Returns
    -------
    str
        Starter configuration as YAML string.
    """
    return STARTER_CONFIG
