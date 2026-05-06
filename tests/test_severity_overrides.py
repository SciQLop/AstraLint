"""Tests for cfg.severity_overrides — overriding the severity of specific rules by reference."""

import pytest
from pydantic import ValidationError

from astralint.base.conformance_suite import (
    ConformanceSuite,
    apply_severity_overrides,
)
from astralint.base.file import Attribute, DataType, File
from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.base.yaml_rules.yaml_rule import YamlRule
from astralint.config import AstraLintConfig


def _yaml_rule(reference: str, severity: Severity) -> YamlRule:
    return YamlRule(
        name=f"Rule-{reference}",
        description="test rule",
        url="",
        reference=reference,
        severity=severity,
        assertions=[{"check": "exists", "path": "attributes/Project"}],
    )


def _empty_file() -> File:
    return File(
        extension="mock",
        filename="empty.mock",
        compression="NONE",
        attributes={
            "Other": Attribute(name="Other", data_type=[DataType.CHAR], shape=[1], values=["x"])
        },
        variables={},
    )


class TestApplySeverityOverrides:
    def test_no_overrides_returns_rules_unchanged(self):
        rules = [_yaml_rule("R-1", Severity.ERROR)]
        assert apply_severity_overrides(rules, {}) is rules

    def test_override_changes_rule_severity(self):
        rules = [_yaml_rule("R-1", Severity.ERROR), _yaml_rule("R-2", Severity.ERROR)]
        out = apply_severity_overrides(rules, {"R-1": Severity.WARNING})
        assert out[0].severity == Severity.WARNING
        assert out[1].severity == Severity.ERROR  # untouched

    def test_unknown_reference_is_noop(self):
        rules = [_yaml_rule("R-1", Severity.ERROR)]
        out = apply_severity_overrides(rules, {"DOES-NOT-EXIST": Severity.WARNING})
        assert out[0].severity == Severity.ERROR

    def test_does_not_mutate_original(self):
        rules = [_yaml_rule("R-1", Severity.ERROR)]
        apply_severity_overrides(rules, {"R-1": Severity.WARNING})
        assert rules[0].severity == Severity.ERROR


class TestSeverityOverridesEndToEnd:
    def test_overridden_severity_propagates_to_results(self):
        rule = _yaml_rule("R-1", Severity.ERROR)
        suite = ConformanceSuite(
            name="T",
            description="",
            url="",
            rules=[rule.model_copy(update={"severity": Severity.WARNING})],
        )
        results = suite.run(_empty_file())
        leaves = _flatten_leaves(results)
        assert all(r.severity == Severity.WARNING for r in leaves if not r.valid)


class TestConfigValidation:
    def test_accepts_valid_severities(self):
        cfg = AstraLintConfig(
            severity_overrides={"R-1": "WARNING", "R-2": "INFO", "R-3": "ERROR"}  # type: ignore[arg-type]
        )
        assert cfg.severity_overrides["R-1"] == Severity.WARNING

    def test_rejects_invalid_severity(self):
        with pytest.raises(ValidationError):
            AstraLintConfig(severity_overrides={"R-1": "BOGUS"})  # type: ignore

    def test_rejects_skipped_as_override(self):
        # SKIPPED is an internal-only severity (condition not met); not a valid override.
        with pytest.raises(ValidationError):
            AstraLintConfig(severity_overrides={"R-1": "SKIPPED"})  # type: ignore


def _flatten_leaves(group: ValidationResultGroup) -> list[ValidationResult]:
    leaves: list[ValidationResult] = []
    for r in group.results:
        if isinstance(r, ValidationResult):
            leaves.append(r)
        else:
            leaves.extend(_flatten_leaves(r))
    return leaves
