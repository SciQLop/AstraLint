"""Tests for the JSON reporter."""

import json
from pathlib import Path

import pytest

from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.reports import report
from astralint.reports.json import generate_json


@pytest.fixture
def mixed_results():
    return ValidationResultGroup(
        name="AstraLint Results",
        rule_reference="",
        severity=Severity.INFO,
        results=[
            ValidationResult(
                valid=True,
                reference="ISTP-001",
                severity=Severity.INFO,
                message="Project attribute present",
            ),
            ValidationResult(
                valid=False,
                reference="ISTP-002",
                severity=Severity.ERROR,
                message="Mission_group missing",
            ),
        ],
    )


class TestGenerateJson:
    def test_emits_valid_json(self, mixed_results):
        out = generate_json(mixed_results)
        parsed = json.loads(out)
        assert parsed["name"] == "AstraLint Results"
        refs = [r["reference"] for r in parsed["results"]]
        assert refs == ["ISTP-001", "ISTP-002"]

    def test_severity_serialized_as_string(self, mixed_results):
        parsed = json.loads(generate_json(mixed_results))
        assert parsed["results"][1]["severity"] == "ERROR"

    def test_preserves_nested_groups(self):
        nested = ValidationResultGroup(
            name="outer",
            rule_reference="",
            severity=Severity.INFO,
            results=[
                ValidationResultGroup(
                    name="inner",
                    rule_reference="R1",
                    severity=Severity.WARNING,
                    results=[
                        ValidationResult(
                            valid=False,
                            reference="R1",
                            severity=Severity.WARNING,
                            message="inner failure",
                        )
                    ],
                )
            ],
        )
        parsed = json.loads(generate_json(nested))
        assert parsed["results"][0]["name"] == "inner"
        assert parsed["results"][0]["results"][0]["reference"] == "R1"


class TestJsonReportEntryPoint:
    def test_writes_to_dest(self, mixed_results, tmp_path: Path):
        dest = tmp_path / "report.json"
        report(mixed_results, output="json", dest=dest)
        parsed = json.loads(dest.read_text())
        assert [r["reference"] for r in parsed["results"]] == ["ISTP-001", "ISTP-002"]

    def test_prints_to_stdout_when_no_dest(self, mixed_results, capsys):
        report(mixed_results, output="json")
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["name"] == "AstraLint Results"

    def test_show_passed_false_filters_passed_leaves(self, mixed_results, capsys):
        report(mixed_results, output="json", show_passed=False)
        parsed = json.loads(capsys.readouterr().out)
        refs = [r["reference"] for r in parsed["results"]]
        assert refs == ["ISTP-002"]
