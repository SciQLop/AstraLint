"""Tests for result-ergonomics improvements:

- documentation URL propagated from the rule to its result group and rendered (#8)
- severity label shown only on failing results (#11)
"""

import io

from rich.console import Console

from astralint.base.file import File
from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)
from astralint.base.yaml_rules.yaml_rule import YamlRule
from astralint.reports import report
from astralint.reports.console import console_report
from astralint.reports.html import generate_html


def _render_console(results: ValidationResultGroup) -> str:
    buf = io.StringIO()
    console = Console(file=buf, width=200, force_terminal=False, color_system=None)
    console_report(results, console)
    return buf.getvalue()


class TestUrlPropagation:
    def test_group_has_url_field_defaulting_to_empty(self):
        group = ValidationResultGroup(
            name="g", rule_reference="R-1", severity=Severity.INFO, results=[]
        )
        assert group.url == ""

    def test_yaml_rule_check_propagates_url_to_group(self):
        rule = YamlRule(
            name="DOIFormat",
            description="DOI format",
            url="https://example.org/istp#DOI",
            reference="ISTP-GA-014",
            severity=Severity.WARNING,
            assertions=[],
        )
        empty_file = File(
            filename="x.cdf", extension="cdf", compression="none", attributes={}, variables={}
        )
        result = rule.check(empty_file)
        assert isinstance(result, ValidationResultGroup)
        assert result.url == "https://example.org/istp#DOI"

    def test_console_renders_url_when_present(self):
        group = ValidationResultGroup(
            name="DOIFormat",
            rule_reference="ISTP-GA-014",
            url="https://example.org/istp#DOI",
            severity=Severity.WARNING,
            results=[
                ValidationResult(
                    valid=False,
                    reference="ISTP-GA-014",
                    severity=Severity.WARNING,
                    message="bad DOI",
                )
            ],
        )
        out = _render_console(group)
        assert "https://example.org/istp#DOI" in out

    def test_html_renders_url_as_link_when_present(self):
        group = ValidationResultGroup(
            name="DOIFormat",
            rule_reference="ISTP-GA-014",
            url="https://example.org/istp#DOI",
            severity=Severity.WARNING,
            results=[
                ValidationResult(
                    valid=False,
                    reference="ISTP-GA-014",
                    severity=Severity.WARNING,
                    message="bad DOI",
                )
            ],
        )
        html = generate_html(group)
        assert 'href="https://example.org/istp#DOI"' in html


class TestHtmlEscaping:
    def _group(self, url: str = "", message: str = "msg") -> ValidationResultGroup:
        return ValidationResultGroup(
            name="R",
            rule_reference="R-1",
            url=url,
            severity=Severity.ERROR,
            results=[
                ValidationResult(
                    valid=False, reference="R-1", severity=Severity.ERROR, message=message
                )
            ],
        )

    def test_message_with_html_is_escaped(self):
        html = generate_html(self._group(message="<script>alert(1)</script>"))
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_url_with_quotes_is_escaped(self):
        html = generate_html(self._group(url='https://x.org/"><img src=x onerror=alert(1)>'))
        assert '"><img' not in html

    def test_javascript_scheme_url_is_not_linked(self):
        html = generate_html(self._group(url="javascript:alert(1)"))
        assert "javascript:alert(1)" not in html


class TestSeverityOnlyOnFailure:
    def _group(self) -> ValidationResultGroup:
        return ValidationResultGroup(
            name="g",
            rule_reference="R-1",
            severity=Severity.ERROR,
            results=[
                ValidationResult(
                    valid=True,
                    reference="R-1",
                    severity=Severity.ERROR,
                    message="passed check",
                ),
                ValidationResult(
                    valid=False,
                    reference="R-2",
                    severity=Severity.ERROR,
                    message="failed check",
                ),
            ],
        )

    def test_console_hides_severity_on_passing_result(self):
        out = _render_console(self._group())
        # The single ERROR label that survives belongs to the failing result only.
        assert out.count("(ERROR)") == 1

    def test_html_hides_severity_badge_on_passing_result(self):
        html = generate_html(self._group())
        # One severity badge span, for the failing result only.
        assert html.count('class="severity ERROR"') == 1


class TestFailuresOnly:
    def _group(self) -> ValidationResultGroup:
        return ValidationResultGroup(
            name="AstraLint Results",
            rule_reference="",
            severity=Severity.INFO,
            results=[
                ValidationResult(
                    valid=True, reference="P-1", severity=Severity.INFO, message="passed"
                ),
                ValidationResult(
                    valid=True, reference="S-1", severity=Severity.SKIPPED, message="skipped"
                ),
                ValidationResult(
                    valid=False, reference="F-1", severity=Severity.ERROR, message="failed"
                ),
            ],
        )

    def test_failures_only_keeps_only_failing_leaves(self):
        pruned = self._group().failures_only()
        refs = [r.reference for r in pruned.results if isinstance(r, ValidationResult)]
        assert refs == ["F-1"]

    def test_failures_only_prunes_emptied_groups(self):
        outer = ValidationResultGroup(
            name="outer",
            rule_reference="",
            severity=Severity.INFO,
            results=[
                ValidationResultGroup(
                    name="all-pass",
                    rule_reference="R-1",
                    severity=Severity.INFO,
                    results=[
                        ValidationResult(
                            valid=True, reference="P-1", severity=Severity.INFO, message="ok"
                        )
                    ],
                )
            ],
        )
        assert outer.failures_only().results == []

    def test_report_failed_only_kwarg(self, capsys):
        report(self._group(), output="console", failed_only=True)
        out = capsys.readouterr().out
        assert "F-1" in out
        assert "P-1" not in out
        assert "S-1" not in out


class TestHtmlFilterBox:
    def _group(self) -> ValidationResultGroup:
        return ValidationResultGroup(
            name="g",
            rule_reference="R-1",
            severity=Severity.ERROR,
            results=[
                ValidationResult(valid=True, reference="P-1", severity=Severity.INFO, message="ok"),
                ValidationResult(
                    valid=False, reference="F-1", severity=Severity.ERROR, message="bad"
                ),
            ],
        )

    def test_html_has_text_filter_input(self):
        html = generate_html(self._group())
        assert 'id="alr-filter"' in html

    def test_html_has_failed_only_toggle(self):
        html = generate_html(self._group())
        assert 'id="alr-failed-only"' in html

    def test_html_filter_script_present(self):
        html = generate_html(self._group())
        assert "applyFilter" in html
