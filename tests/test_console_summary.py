"""Tests for the linter-style quiet console output: a flat findings list plus a
verdict/summary line, quiet (failures-only) by default."""

from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.reports import report


def _file_results(filename: str, *rules: ValidationResultGroup) -> ValidationResultGroup:
    file_group = ValidationResultGroup(
        name=f"AstraLint Results for suite 'ISTP' on file '{filename}'",
        rule_reference="",
        severity=Severity.INFO,
        results=list(rules),
    )
    return ValidationResultGroup(
        name="AstraLint Results",
        rule_reference="",
        severity=Severity.INFO,
        results=[file_group],
    )


def _rule(reference: str, severity: Severity, *leaves: ValidationResult) -> ValidationResultGroup:
    return ValidationResultGroup(
        name=reference,
        rule_reference=reference,
        severity=severity,
        results=list(leaves),
    )


def _leaf(
    valid: bool, severity: Severity, message: str, target: str = "Global"
) -> ValidationResult:
    return ValidationResult(
        valid=valid, reference="", severity=severity, message=message, target=target
    )


def _mixed() -> ValidationResultGroup:
    return _file_results(
        "my.cdf",
        _rule(
            "ISTP-GA-004",
            Severity.ERROR,
            _leaf(False, Severity.ERROR, "bad logical_file_id", "Logical_file_id"),
        ),
        _rule(
            "ISTP-GA-005",
            Severity.WARNING,
            _leaf(True, Severity.WARNING, "version ok", "Data_version"),
        ),
        _rule(
            "ISTP-GA-010",
            Severity.WARNING,
            _leaf(False, Severity.WARNING, "non-standard instrument type", "Instrument_type"),
        ),
    )


class TestSummaryLine:
    def test_summary_counts_failures_by_severity(self, capsys):
        report(_mixed(), output="console")
        out = capsys.readouterr().out
        assert "2 problems" in out
        assert "1 error" in out
        assert "1 warning" in out

    def test_all_passed_shows_success_verdict(self, capsys):
        passing = _file_results(
            "ok.cdf",
            _rule("ISTP-GA-005", Severity.WARNING, _leaf(True, Severity.WARNING, "ok", "X")),
        )
        report(passing, output="console")
        out = capsys.readouterr().out
        assert "passed" in out.lower()
        assert "problem" not in out.lower()


class TestQuietDefault:
    def test_default_hides_passing_findings(self, capsys):
        report(_mixed(), output="console")
        out = capsys.readouterr().out
        assert "ISTP-GA-004" in out  # failing error
        assert "ISTP-GA-010" in out  # failing warning
        assert "ISTP-GA-005" not in out  # passing, hidden by default

    def test_default_shows_filename_and_codes(self, capsys):
        report(_mixed(), output="console")
        out = capsys.readouterr().out
        assert "my.cdf" in out

    def test_errors_listed_before_warnings(self, capsys):
        report(_mixed(), output="console")
        out = capsys.readouterr().out
        assert out.index("ISTP-GA-004") < out.index("ISTP-GA-010")

    def test_show_passed_reveals_passing_findings(self, capsys):
        report(_mixed(), output="console", show_passed=True)
        out = capsys.readouterr().out
        assert "ISTP-GA-005" in out


class TestInfoHandling:
    def _with_info(self) -> ValidationResultGroup:
        return _file_results(
            "my.cdf",
            _rule(
                "ISTP-GA-004",
                Severity.ERROR,
                _leaf(False, Severity.ERROR, "bad logical_file_id", "Logical_file_id"),
            ),
            _rule(
                "ISTP-INFO-001",
                Severity.INFO,
                _leaf(False, Severity.INFO, "could add COORDINATE_SYSTEM", "var_a"),
                _leaf(False, Severity.INFO, "could add COORDINATE_SYSTEM", "var_b"),
            ),
        )

    def test_info_not_listed_by_default(self, capsys):
        report(self._with_info(), output="console")
        out = capsys.readouterr().out
        assert "COORDINATE_SYSTEM" not in out
        assert "ISTP-GA-004" in out

    def test_info_counted_separately_not_as_problems(self, capsys):
        report(self._with_info(), output="console")
        out = capsys.readouterr().out
        assert "1 problem" in out  # only the error
        assert "2 info" in out  # info surfaced as a count

    def test_show_passed_lists_info(self, capsys):
        report(self._with_info(), output="console", show_passed=True)
        out = capsys.readouterr().out
        assert "COORDINATE_SYSTEM" in out


class TestHtmlUnaffectedByDefault:
    def test_html_default_keeps_passing_results(self, capsys):
        report(_mixed(), output="html")
        out = capsys.readouterr().out
        # HTML stays comprehensive (filter box narrows client-side), passing rule present.
        assert "version ok" in out


class TestConsoleDestAndFailedOnly:
    def test_dest_writes_console_output_to_file(self, tmp_path):
        dest = tmp_path / "report.txt"
        report(_mixed(), output="console", dest=dest)
        content = dest.read_text()
        assert "ISTP-GA-004" in content
        assert "Found" in content

    def test_failed_only_prunes_tree_even_with_show_passed(self, capsys):
        report(_mixed(), output="console", show_passed=True, failed_only=True)
        out = capsys.readouterr().out
        assert "ISTP-GA-004" in out  # failing rule kept
        assert "version ok" not in out  # passing leaf pruned despite show_passed


class TestTreeEmptyTarget:
    def test_tree_omits_at_for_empty_target(self, capsys):
        group = ValidationResultGroup(
            name="R",
            rule_reference="R-1",
            severity=Severity.ERROR,
            results=[
                ValidationResult(
                    valid=False, reference="R-1", severity=Severity.ERROR, message="m", target=""
                )
            ],
        )
        report(group, output="console", show_passed=True)
        out = capsys.readouterr().out
        assert "@ " not in out
