"""Tests for report rendering (console and HTML), focused on show_passed filtering."""

import io

import pytest
from rich.console import Console

from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.reports import report
from astralint.reports.console import console_report
from astralint.reports.html import generate_html


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


def _render_console(results, show_passed: bool) -> str:
    buf = io.StringIO()
    console = Console(file=buf, width=200, force_terminal=False, color_system=None)
    rendered = results if show_passed else results.without_passed()
    console_report(rendered, console)
    return buf.getvalue()


class TestConsoleShowPassed:
    def test_show_passed_true_renders_passed_leaves(self, mixed_results):
        out = _render_console(mixed_results, show_passed=True)
        assert "ISTP-001" in out
        assert "ISTP-002" in out

    def test_show_passed_false_hides_passed_leaves(self, mixed_results):
        out = _render_console(mixed_results, show_passed=False)
        assert "ISTP-001" not in out
        assert "ISTP-002" in out


class TestHtmlShowPassed:
    def test_show_passed_true_renders_passed_leaves(self, mixed_results):
        html = generate_html(mixed_results)
        assert "ISTP-001" in html
        assert "ISTP-002" in html

    def test_show_passed_false_hides_passed_leaves(self, mixed_results):
        filtered = mixed_results.without_passed()
        html = generate_html(filtered)
        assert "ISTP-001" not in html
        assert "ISTP-002" in html


class TestReportEntryPoint:
    def test_report_accepts_show_passed_kwarg(self, mixed_results, capsys):
        report(mixed_results, output="console", show_passed=False)
        out = capsys.readouterr().out
        assert "ISTP-001" not in out
        assert "ISTP-002" in out
