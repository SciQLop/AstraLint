"""Tests for configuration loading."""

import pytest
from pathlib import Path
import tempfile
import os

from astralint.config import AstraLintConfig, load_config, validate_config_file
from astralint.config.loader import merge_configs, generate_starter_config


class TestAstraLintConfig:
    """Tests for AstraLintConfig schema."""

    def test_default_config(self):
        """Default config has expected values."""
        cfg = AstraLintConfig()
        assert cfg.suite == "ISTP"
        assert cfg.select == []
        assert cfg.ignore == []
        assert cfg.output.format == "console"
        assert cfg.output.verbose is False
        assert cfg.output.show_passed is True

    def test_config_with_values(self):
        """Config accepts valid values."""
        cfg = AstraLintConfig(
            suite="PDS4",
            select=["rule1", "rule2"],
            ignore=["deprecated"],
            severity_overrides={"RULE-001": "WARNING"},
        )
        assert cfg.suite == "PDS4"
        assert cfg.select == ["rule1", "rule2"]
        assert cfg.ignore == ["deprecated"]
        assert cfg.severity_overrides == {"RULE-001": "WARNING"}

    def test_config_rejects_unknown_fields(self):
        """Config with unknown fields raises error."""
        with pytest.raises(Exception):
            AstraLintConfig(unknown_field="value")

    def test_nested_output_config(self):
        """Nested output config works correctly."""
        cfg = AstraLintConfig(
            output={"format": "html", "verbose": True}
        )
        assert cfg.output.format == "html"
        assert cfg.output.verbose is True


class TestMergeConfigs:
    """Tests for config merging."""

    def test_merge_simple(self):
        """Simple config merge works."""
        base = {"suite": "ISTP", "select": ["rule1"]}
        override = {"suite": "PDS4"}
        result = merge_configs(base, override)
        assert result["suite"] == "PDS4"
        assert result["select"] == ["rule1"]

    def test_merge_nested(self):
        """Nested config merge works."""
        base = {"output": {"format": "console", "verbose": False}}
        override = {"output": {"verbose": True}}
        result = merge_configs(base, override)
        assert result["output"]["format"] == "console"
        assert result["output"]["verbose"] is True

    def test_merge_adds_new_keys(self):
        """Merge adds new keys from override."""
        base = {"suite": "ISTP"}
        override = {"select": ["rule1"]}
        result = merge_configs(base, override)
        assert result["suite"] == "ISTP"
        assert result["select"] == ["rule1"]

    def test_merge_empty_base(self):
        """Merge with empty base works."""
        base = {}
        override = {"suite": "PDS4", "select": ["rule1"]}
        result = merge_configs(base, override)
        assert result == override

    def test_merge_empty_override(self):
        """Merge with empty override returns base."""
        base = {"suite": "ISTP"}
        override = {}
        result = merge_configs(base, override)
        assert result == base


class TestStarterConfig:
    """Tests for starter config generation."""

    def test_starter_config_is_valid_yaml(self):
        """Generated starter config is valid YAML."""
        import yaml
        content = generate_starter_config()
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "suite" in data

    def test_starter_config_validates(self):
        """Generated starter config passes schema validation."""
        import yaml
        content = generate_starter_config()
        data = yaml.safe_load(content)
        cfg = AstraLintConfig(**data)
        assert cfg.suite == "ISTP"


class TestLoadConfig:
    """Tests for config loading from files."""

    def test_load_config_defaults(self):
        """load_config returns defaults when no config files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = load_config(project_root=Path(tmpdir))
            assert cfg.suite == "ISTP"

    def test_load_config_from_yaml(self):
        """load_config reads from .astralint.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".astralint.yaml"
            config_path.write_text("suite: PDS4\nselect:\n  - rule1\n")

            cfg = load_config(project_root=Path(tmpdir))
            assert cfg.suite == "PDS4"
            assert cfg.select == ["rule1"]

    def test_load_config_cli_overrides(self):
        """CLI overrides take precedence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".astralint.yaml"
            config_path.write_text("suite: PDS4\n")

            cfg = load_config(
                project_root=Path(tmpdir),
                cli_overrides={"suite": "ISTP"}
            )
            assert cfg.suite == "ISTP"

    def test_load_config_explicit_file(self):
        """Explicit config file is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create default config
            default_config = Path(tmpdir) / ".astralint.yaml"
            default_config.write_text("suite: ISTP\n")

            # Create explicit config in different location
            explicit_config = Path(tmpdir) / "custom.yaml"
            explicit_config.write_text("suite: PDS4\n")

            cfg = load_config(
                project_root=Path(tmpdir),
                config_file=explicit_config
            )
            assert cfg.suite == "PDS4"


class TestValidateConfigFile:
    """Tests for config file validation."""

    def test_validate_valid_yaml(self):
        """Valid YAML config passes validation."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"suite: ISTP\nselect: []\n")
            f.flush()

            is_valid, error = validate_config_file(Path(f.name))
            assert is_valid is True
            assert error is None

            os.unlink(f.name)

    def test_validate_invalid_yaml(self):
        """Invalid YAML config fails validation."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"suite: ISTP\nunknown_field: value\n")
            f.flush()

            is_valid, error = validate_config_file(Path(f.name))
            assert is_valid is False
            assert error is not None
            assert "unknown_field" in error.lower() or "extra" in error.lower()

            os.unlink(f.name)

    def test_validate_malformed_yaml(self):
        """Malformed YAML fails validation."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"suite: [\n")  # Invalid YAML
            f.flush()

            is_valid, error = validate_config_file(Path(f.name))
            assert is_valid is False
            assert error is not None

            os.unlink(f.name)


@pytest.mark.parametrize("severity", ["ERROR", "WARNING", "INFO"])
def test_severity_overrides_valid_values(severity):
    """Severity overrides accept valid severity values."""
    cfg = AstraLintConfig(severity_overrides={"RULE-001": severity})
    assert cfg.severity_overrides["RULE-001"] == severity

