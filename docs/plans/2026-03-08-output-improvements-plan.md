# Output Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rework console output to show only problems by default (like ruff/eslint), with flat and grouped formats, a summary line, and human-readable messages.

**Architecture:** Add a transform pipeline (`ValidationResultGroup` → flat `Issue` list → filter → format). Rule engine stays untouched. Three new files in `src/astralint/reports/`: `transform.py`, `flat.py`, `grouped.py`. Config model and CLI updated for `--format` and `--all` flags.

**Tech Stack:** Python 3.11+, Pydantic, Rich (console output), pytest

---

### Task 1: Issue Dataclass and Path Parser

**Files:**
- Create: `src/astralint/reports/transform.py`
- Test: `tests/test_report_transform.py`

**Step 1: Write failing tests for path parsing**

```python
import pytest
from astralint.reports.transform import parse_path


@pytest.mark.parametrize(
    "path, expected_variable, expected_attribute",
    [
        ("variables/B/attributes/CATDESC/values/0", "B", "CATDESC"),
        ("variables/Epoch/attributes/UNITS/values/0", "Epoch", "UNITS"),
        ("variables/B/data_type", "B", None),
        ("attributes/Logical_file_id/values/0", None, "Logical_file_id"),
        ("attributes", None, None),
        ("Global", None, None),
        ("variables/.*/attributes/CATDESC/values/[0-9]*", None, "CATDESC"),
    ],
)
def test_parse_path(path, expected_variable, expected_attribute):
    variable, attribute = parse_path(path)
    assert variable == expected_variable
    assert attribute == expected_attribute
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_transform.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'astralint.reports.transform'`

**Step 3: Write the Issue dataclass and parse_path**

```python
"""Transform validation result trees into flat Issue lists for formatting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ..base import Severity

_PATH_PATTERN = re.compile(
    r"^variables/(?P<var>[^/]+)/attributes/(?P<attr>[^/]+)"
    r"|^variables/(?P<var_only>[^/]+)"
    r"|^attributes/(?P<attr_only>[^/]+)"
)


class Verbosity(Enum):
    NORMAL = "normal"
    ALL = "all"


@dataclass(frozen=True)
class Issue:
    rule_id: str
    rule_name: str
    severity: Severity
    passed: bool
    message: str
    variable: str | None
    attribute: str | None
    raw_path: str


def parse_path(path: str) -> tuple[str | None, str | None]:
    """Extract variable and attribute names from a validation result path."""
    m = _PATH_PATTERN.search(path)
    if not m:
        return None, None
    if m.group("var") and m.group("attr"):
        var = m.group("var")
        return (var if var != ".*" else None), m.group("attr")
    if m.group("var_only"):
        var = m.group("var_only")
        return (var if var != ".*" else None), None
    if m.group("attr_only"):
        return None, m.group("attr_only")
    return None, None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report_transform.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astralint/reports/transform.py tests/test_report_transform.py
git commit -m "feat: add Issue dataclass and path parser for report transform"
```

---

### Task 2: Flatten Function

**Files:**
- Modify: `src/astralint/reports/transform.py`
- Modify: `tests/test_report_transform.py`

**Step 1: Write failing tests for flatten**

```python
from astralint.base import Severity, ValidationResult, ValidationResultGroup
from astralint.reports.transform import Issue, flatten


def test_flatten_single_result():
    group = ValidationResultGroup(
        name="TestRule",
        rule_reference="ISTP-GA-001",
        severity=Severity.ERROR,
        results=[
            ValidationResult(
                valid=False,
                reference="",
                severity=Severity.ERROR,
                message="Missing attribute",
                target="attributes/Logical_source/values/0",
            )
        ],
    )
    issues = flatten(group)
    assert len(issues) == 1
    assert issues[0].rule_id == "ISTP-GA-001"
    assert issues[0].rule_name == "TestRule"
    assert issues[0].passed is False
    assert issues[0].attribute == "Logical_source"
    assert issues[0].variable is None


def test_flatten_nested_groups():
    inner = ValidationResultGroup(
        name="InnerRule",
        rule_reference="ISTP-VA-001",
        severity=Severity.WARNING,
        results=[
            ValidationResult(
                valid=True,
                reference="",
                severity=Severity.WARNING,
                message="All good",
                target="variables/B/attributes/CATDESC/values/0",
            )
        ],
    )
    outer = ValidationResultGroup(
        name="AstraLint Results",
        rule_reference="",
        severity=Severity.INFO,
        results=[inner],
    )
    issues = flatten(outer)
    assert len(issues) == 1
    assert issues[0].rule_id == "ISTP-VA-001"
    assert issues[0].rule_name == "InnerRule"
    assert issues[0].variable == "B"
    assert issues[0].attribute == "CATDESC"
    assert issues[0].passed is True


def test_flatten_wrapper_groups_inherit_rule_id():
    """Groups with empty rule_reference (wrappers like 'AstraLint Results') don't override."""
    leaf = ValidationResult(
        valid=False,
        reference="",
        severity=Severity.ERROR,
        message="Bad",
        target="attributes/DOI/values/0",
    )
    rule_group = ValidationResultGroup(
        name="DOIFormat",
        rule_reference="ISTP-GA-014",
        severity=Severity.WARNING,
        results=[
            ValidationResultGroup(
                name="MatchesAssertion",
                rule_reference="",
                severity=Severity.WARNING,
                results=[leaf],
            )
        ],
    )
    wrapper = ValidationResultGroup(
        name="AstraLint Results",
        rule_reference="",
        severity=Severity.INFO,
        results=[rule_group],
    )
    issues = flatten(wrapper)
    assert len(issues) == 1
    assert issues[0].rule_id == "ISTP-GA-014"
    assert issues[0].rule_name == "DOIFormat"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_transform.py::test_flatten_single_result -v`
Expected: FAIL — `ImportError: cannot import name 'flatten'`

**Step 3: Implement flatten**

Add to `src/astralint/reports/transform.py`:

```python
from ..base import ValidationResult, ValidationResultGroup


def flatten(result_tree: ValidationResultGroup) -> list[Issue]:
    """Walk the result tree and produce a flat list of Issues."""
    issues: list[Issue] = []
    _walk(result_tree, rule_id="", rule_name="", issues=issues)
    return issues


def _walk(
    node: ValidationResult | ValidationResultGroup,
    rule_id: str,
    rule_name: str,
    issues: list[Issue],
) -> None:
    if isinstance(node, ValidationResult):
        variable, attribute = parse_path(node.target)
        issues.append(
            Issue(
                rule_id=rule_id,
                rule_name=rule_name,
                severity=node.severity,
                passed=node.valid,
                message=node.message,
                variable=variable,
                attribute=attribute,
                raw_path=node.target,
            )
        )
    elif isinstance(node, ValidationResultGroup):
        current_rule_id = node.rule_reference or rule_id
        current_rule_name = node.name if node.rule_reference else rule_name
        for child in node.results:
            _walk(child, current_rule_id, current_rule_name, issues)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report_transform.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astralint/reports/transform.py tests/test_report_transform.py
git commit -m "feat: add flatten function to transform result tree into Issue list"
```

---

### Task 3: Filter Function

**Files:**
- Modify: `src/astralint/reports/transform.py`
- Modify: `tests/test_report_transform.py`

**Step 1: Write failing tests for filter_issues**

```python
from astralint.reports.transform import Issue, Verbosity, filter_issues


def _make_issue(severity: Severity, passed: bool) -> Issue:
    return Issue(
        rule_id="R-001",
        rule_name="Rule",
        severity=severity,
        passed=passed,
        message="msg",
        variable=None,
        attribute=None,
        raw_path="",
    )


def test_filter_normal_keeps_failed_errors_and_warnings():
    issues = [
        _make_issue(Severity.ERROR, passed=False),
        _make_issue(Severity.WARNING, passed=False),
        _make_issue(Severity.ERROR, passed=True),
        _make_issue(Severity.WARNING, passed=True),
        _make_issue(Severity.INFO, passed=False),
        _make_issue(Severity.SKIPPED, passed=True),
    ]
    result = filter_issues(issues, Verbosity.NORMAL)
    assert len(result) == 2
    assert all(not i.passed for i in result)
    assert {i.severity for i in result} == {Severity.ERROR, Severity.WARNING}


def test_filter_all_keeps_everything():
    issues = [
        _make_issue(Severity.ERROR, passed=True),
        _make_issue(Severity.WARNING, passed=False),
        _make_issue(Severity.INFO, passed=True),
        _make_issue(Severity.SKIPPED, passed=True),
    ]
    result = filter_issues(issues, Verbosity.ALL)
    assert len(result) == 4
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_transform.py::test_filter_normal_keeps_failed_errors_and_warnings -v`
Expected: FAIL — `ImportError: cannot import name 'filter_issues'`

**Step 3: Implement filter_issues**

Add to `src/astralint/reports/transform.py`:

```python
def filter_issues(issues: list[Issue], verbosity: Verbosity) -> list[Issue]:
    """Filter issues based on verbosity level."""
    if verbosity == Verbosity.ALL:
        return issues
    return [
        i for i in issues
        if not i.passed and i.severity in (Severity.ERROR, Severity.WARNING)
    ]
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report_transform.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astralint/reports/transform.py tests/test_report_transform.py
git commit -m "feat: add filter_issues for verbosity-based filtering"
```

---

### Task 4: Summary Line Function

**Files:**
- Modify: `src/astralint/reports/transform.py`
- Modify: `tests/test_report_transform.py`

**Step 1: Write failing tests for summary_line**

```python
from astralint.reports.transform import summary_line


def test_summary_line_with_issues():
    issues = [  # all issues (unfiltered) for counting
        _make_issue(Severity.ERROR, passed=False),
        _make_issue(Severity.ERROR, passed=False),
        _make_issue(Severity.WARNING, passed=False),
        _make_issue(Severity.ERROR, passed=True),
        _make_issue(Severity.WARNING, passed=True),
    ]
    result = summary_line(issues, filename="test.cdf", suite="ISTP")
    assert result == "test.cdf [ISTP]: 2 errors, 1 warning (2 passed)"


def test_summary_line_no_issues():
    issues = [
        _make_issue(Severity.ERROR, passed=True),
        _make_issue(Severity.WARNING, passed=True),
    ]
    result = summary_line(issues, filename="test.cdf", suite="ISTP")
    assert result == "test.cdf [ISTP]: 0 errors, 0 warnings (2 passed)"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_transform.py::test_summary_line_with_issues -v`
Expected: FAIL — `ImportError: cannot import name 'summary_line'`

**Step 3: Implement summary_line**

Add to `src/astralint/reports/transform.py`:

```python
def summary_line(all_issues: list[Issue], filename: str, suite: str) -> str:
    """Produce a summary line like: 'file.cdf [ISTP]: 2 errors, 1 warning (48 passed)'."""
    errors = sum(1 for i in all_issues if not i.passed and i.severity == Severity.ERROR)
    warnings = sum(1 for i in all_issues if not i.passed and i.severity == Severity.WARNING)
    passed = sum(1 for i in all_issues if i.passed)
    error_s = "error" if errors == 1 else "errors"
    warning_s = "warning" if warnings == 1 else "warnings"
    return f"{filename} [{suite}]: {errors} {error_s}, {warnings} {warning_s} ({passed} passed)"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report_transform.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astralint/reports/transform.py tests/test_report_transform.py
git commit -m "feat: add summary_line function for report footer"
```

---

### Task 5: Flat Formatter

**Files:**
- Create: `src/astralint/reports/flat.py`
- Create: `tests/test_report_flat.py`

**Step 1: Write failing tests**

```python
from io import StringIO

from rich.console import Console

from astralint.base import Severity
from astralint.reports.flat import flat_report
from astralint.reports.transform import Issue


def _make_issue(
    severity: Severity,
    passed: bool,
    rule_id: str = "ISTP-GA-001",
    rule_name: str = "Rule",
    message: str = "something went wrong",
    variable: str | None = None,
    attribute: str | None = "Foo",
) -> Issue:
    return Issue(
        rule_id=rule_id,
        rule_name=rule_name,
        severity=severity,
        passed=passed,
        message=message,
        variable=variable,
        attribute=attribute,
        raw_path="",
    )


def test_flat_report_shows_failures(capsys):
    issues = [
        _make_issue(Severity.ERROR, passed=False, attribute="Logical_file_id"),
        _make_issue(
            Severity.WARNING,
            passed=False,
            rule_id="ISTP-VA-008",
            variable="B",
            attribute="LABLAXIS",
            message="length 12 exceeds maximum 10",
        ),
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True)
    flat_report(issues, all_issues=issues, filename="test.cdf", suite="ISTP", console=console)
    output = buf.getvalue()
    assert "ERROR" in output
    assert "ISTP-GA-001" in output
    assert "WARN" in output
    assert "ISTP-VA-008" in output
    assert "test.cdf [ISTP]" in output


def test_flat_report_location_global_attribute():
    issues = [
        _make_issue(Severity.ERROR, passed=False, variable=None, attribute="DOI"),
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True)
    flat_report(issues, all_issues=issues, filename="f.cdf", suite="S", console=console)
    output = buf.getvalue()
    assert "DOI" in output


def test_flat_report_location_variable_attribute():
    issues = [
        _make_issue(Severity.ERROR, passed=False, variable="B", attribute="CATDESC"),
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True)
    flat_report(issues, all_issues=issues, filename="f.cdf", suite="S", console=console)
    output = buf.getvalue()
    assert "Variable 'B'" in output
    assert "CATDESC" in output
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_flat.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement flat formatter**

```python
"""Flat one-line-per-issue console formatter."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..base import Severity
from .transform import Issue, summary_line

_SEVERITY_STYLE = {
    Severity.ERROR: ("ERROR", "bold red"),
    Severity.WARNING: ("WARN ", "bold yellow"),
    Severity.INFO: ("INFO ", "bold blue"),
    Severity.SKIPPED: ("SKIP ", "dim"),
}

_PASS_ICON = "[bold green]✔[/]"
_FAIL_ICON = "[bold red]✘[/]"


def _format_location(issue: Issue) -> str:
    if issue.variable and issue.attribute:
        return f"Variable '{issue.variable}', {issue.attribute}"
    if issue.variable:
        return f"Variable '{issue.variable}'"
    if issue.attribute:
        return issue.attribute
    return ""


def flat_report(
    issues: list[Issue],
    all_issues: list[Issue],
    filename: str,
    suite: str,
    console: Console,
) -> None:
    """Print issues in flat one-line-per-issue format with a summary."""
    for issue in issues:
        label, style = _SEVERITY_STYLE.get(issue.severity, ("?????", ""))
        icon = _PASS_ICON if issue.passed else _FAIL_ICON
        location = _format_location(issue)
        location_part = f" {location}:" if location else ""

        line = Text.from_markup(f"{icon} {label} ")
        line.append(f"[{issue.rule_id}]", style="dim")
        line.append(f"{location_part} {issue.message}")

        console.print(line)

    console.print()
    console.print(summary_line(all_issues, filename, suite))
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report_flat.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astralint/reports/flat.py tests/test_report_flat.py
git commit -m "feat: add flat one-line-per-issue console formatter"
```

---

### Task 6: Grouped Formatter

**Files:**
- Create: `src/astralint/reports/grouped.py`
- Create: `tests/test_report_grouped.py`

**Step 1: Write failing tests**

```python
from io import StringIO

from rich.console import Console

from astralint.base import Severity
from astralint.reports.grouped import grouped_report
from astralint.reports.transform import Issue


def _make_issue(
    severity: Severity,
    passed: bool,
    variable: str | None = None,
    attribute: str | None = None,
    rule_id: str = "R-001",
    message: str = "problem",
) -> Issue:
    return Issue(
        rule_id=rule_id,
        rule_name="Rule",
        severity=severity,
        passed=passed,
        message=message,
        variable=variable,
        attribute=attribute,
        raw_path="",
    )


def test_grouped_report_groups_by_variable():
    issues = [
        _make_issue(Severity.ERROR, False, variable="B", attribute="CATDESC"),
        _make_issue(Severity.WARNING, False, variable="B", attribute="UNITS"),
        _make_issue(Severity.ERROR, False, variable="Epoch", attribute="FORMAT"),
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True)
    grouped_report(issues, all_issues=issues, filename="f.cdf", suite="ISTP", console=console)
    output = buf.getvalue()
    assert "Variable 'B'" in output
    assert "Variable 'Epoch'" in output


def test_grouped_report_global_attributes():
    issues = [
        _make_issue(Severity.ERROR, False, variable=None, attribute="DOI"),
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True)
    grouped_report(issues, all_issues=issues, filename="f.cdf", suite="ISTP", console=console)
    output = buf.getvalue()
    assert "Global attribute 'DOI'" in output


def test_grouped_report_summary():
    issues = [
        _make_issue(Severity.ERROR, False),
        _make_issue(Severity.ERROR, True),
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True)
    grouped_report(issues, all_issues=issues, filename="f.cdf", suite="S", console=console)
    output = buf.getvalue()
    assert "f.cdf [S]" in output
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report_grouped.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement grouped formatter**

```python
"""Grouped-by-variable console formatter."""

from __future__ import annotations

from itertools import groupby

from rich.console import Console
from rich.text import Text

from ..base import Severity
from .transform import Issue, summary_line

_SEVERITY_STYLE = {
    Severity.ERROR: ("ERROR", "bold red"),
    Severity.WARNING: ("WARN ", "bold yellow"),
    Severity.INFO: ("INFO ", "bold blue"),
    Severity.SKIPPED: ("SKIP ", "dim"),
}

_PASS_ICON = "[bold green]✔[/]"
_FAIL_ICON = "[bold red]✘[/]"


def _group_key(issue: Issue) -> str:
    if issue.variable:
        return f"Variable '{issue.variable}'"
    if issue.attribute:
        return f"Global attribute '{issue.attribute}'"
    return "General"


def _sort_key(issue: Issue) -> tuple[int, str]:
    """Sort: global attributes first, then variables alphabetically."""
    if issue.variable:
        return (1, issue.variable)
    if issue.attribute:
        return (0, issue.attribute)
    return (2, "")


def grouped_report(
    issues: list[Issue],
    all_issues: list[Issue],
    filename: str,
    suite: str,
    console: Console,
) -> None:
    """Print issues grouped by variable/attribute with a summary."""
    sorted_issues = sorted(issues, key=_sort_key)

    for group_name, group_issues in groupby(sorted_issues, key=_group_key):
        console.print(f"\n[bold]{group_name}:[/]")
        for issue in group_issues:
            label, style = _SEVERITY_STYLE.get(issue.severity, ("?????", ""))
            icon = _PASS_ICON if issue.passed else _FAIL_ICON
            attr_part = f", {issue.attribute}" if issue.variable and issue.attribute else ""

            line = Text.from_markup(f"  {icon} {label} ")
            line.append(f"[{issue.rule_id}]", style="dim")
            line.append(f"{attr_part}: {issue.message}" if attr_part else f" {issue.message}")
            console.print(line)

    console.print()
    console.print(summary_line(all_issues, filename, suite))
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report_grouped.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astralint/reports/grouped.py tests/test_report_grouped.py
git commit -m "feat: add grouped-by-variable console formatter"
```

---

### Task 7: Update Config Model

**Files:**
- Modify: `src/astralint/config/schema.py:9-15`
- Modify: `tests/test_config.py`

**Step 1: Write failing test**

```python
from astralint.config.schema import OutputConfig


def test_output_config_format_accepts_new_values():
    cfg = OutputConfig(format="flat")
    assert cfg.format == "flat"
    cfg2 = OutputConfig(format="grouped")
    assert cfg2.format == "grouped"
    cfg3 = OutputConfig(format="tree")
    assert cfg3.format == "tree"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py::test_output_config_format_accepts_new_values -v`
Expected: FAIL — Pydantic validation error (current Literal doesn't include flat/grouped/tree)

**Step 3: Update OutputConfig**

In `src/astralint/config/schema.py`, change `OutputConfig`:

```python
class OutputConfig(BaseModel):
    """Output configuration settings."""

    format: Literal["flat", "grouped", "tree", "html", "json"] = "flat"
    verbose: bool = False
    show_passed: bool = True
    dest: Path | None = None
```

- `"console"` is replaced by `"flat"` (new default)
- `"tree"` preserves old behavior
- `show_passed` is kept but will be driven by `--all` flag

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (may need to update other tests that use `format="console"`)

**Step 5: Fix any broken tests that reference `format="console"`**

Search for `format="console"` or `"console"` in test files and config loader. Update to `"flat"` or `"tree"` as appropriate. The config loader in `src/astralint/config/loader.py` may also need updating if it references `"console"`.

**Step 6: Commit**

```bash
git add src/astralint/config/schema.py tests/test_config.py
git commit -m "feat: update OutputConfig to support flat/grouped/tree formats"
```

---

### Task 8: Update Report Dispatcher

**Files:**
- Modify: `src/astralint/reports/__init__.py`
- Modify: `src/astralint/reports/console.py` (rename entry point to `tree_report`)

**Step 1: Update the dispatcher**

Replace `src/astralint/reports/__init__.py`:

```python
from pathlib import Path

from rich.console import Console

from ..base import ValidationResultGroup
from .console import report as tree_report
from .flat import flat_report
from .grouped import grouped_report
from .html import report as html_report
from .transform import Verbosity, filter_issues, flatten, summary_line


def report(
    results: ValidationResultGroup,
    output: str = "flat",
    dest: Path | None = None,
    show_all: bool = False,
    filename: str = "",
    suite: str = "",
) -> None:
    """Main entry point for report generation."""
    if output == "html":
        return html_report(results, dest)

    if output == "tree":
        return tree_report(results, dest)

    console = Console()
    all_issues = flatten(results)
    verbosity = Verbosity.ALL if show_all else Verbosity.NORMAL
    filtered = filter_issues(all_issues, verbosity)

    if output == "flat":
        flat_report(filtered, all_issues, filename, suite, console)
    elif output == "grouped":
        grouped_report(filtered, all_issues, filename, suite, console)
    else:
        raise ValueError(f"Unknown output format '{output}'.")
```

**Step 2: Run all tests**

Run: `uv run pytest -v`
Expected: Some tests may fail due to changed `report()` signature — fix in next task.

**Step 3: Commit**

```bash
git add src/astralint/reports/__init__.py
git commit -m "feat: update report dispatcher to route flat/grouped/tree formats"
```

---

### Task 9: Update CLI

**Files:**
- Modify: `src/astralint/astralint.py:118-212`

**Step 1: Update the lint command**

Key changes to the `lint` function:

1. Replace `verbose: bool` with `show_all: bool` (`--all` flag)
2. Pass `filename` and `suite` to `report()`
3. Keep `verbose` as alias for backward compat if desired

```python
@app.command()
def lint(
    path: list[Path],
    suite: str | None = None,
    select: list[str] | None = None,
    ignore: list[str] | None = None,
    config_file: Path | None = None,
    output: str | None = None,
    dest: Path | None = None,
    verbose: bool = False,
    strict: bool = False,
    show_all: bool = False,
):
```

In the body, update the `report()` call:

```python
report(
    results,
    output=cfg.output.format,
    dest=cfg.output.dest,
    show_all=show_all or cfg.output.show_passed is False,  # backward compat
    filename=path[0].name if len(path) == 1 else f"{len(path)} files",
    suite=cfg.suite,
)
```

**Step 2: Run the full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 3: Manual smoke test**

Run against a real file if available:
```bash
uv run astralint lint --format flat ~/Downloads/some_file.cdf
uv run astralint lint --format grouped ~/Downloads/some_file.cdf
uv run astralint lint --format tree ~/Downloads/some_file.cdf
uv run astralint lint --format flat --all ~/Downloads/some_file.cdf
```

**Step 4: Commit**

```bash
git add src/astralint/astralint.py
git commit -m "feat: wire new output formats and --all flag into CLI"
```

---

### Task 10: Final Integration Test

**Files:**
- Modify: `tests/test_report_transform.py`

**Step 1: Write an end-to-end test**

```python
from astralint.base import Severity, ValidationResult, ValidationResultGroup
from astralint.reports.transform import Verbosity, filter_issues, flatten, summary_line


def test_full_pipeline():
    """End-to-end: tree → flatten → filter → summary."""
    tree = ValidationResultGroup(
        name="AstraLint Results",
        rule_reference="",
        severity=Severity.INFO,
        results=[
            ValidationResultGroup(
                name="Suite Results",
                rule_reference="",
                severity=Severity.INFO,
                results=[
                    ValidationResultGroup(
                        name="LogicalFileIdFormat",
                        rule_reference="ISTP-GA-004",
                        severity=Severity.ERROR,
                        results=[
                            ValidationResult(
                                valid=False,
                                reference="",
                                severity=Severity.ERROR,
                                message="does not match pattern",
                                target="attributes/Logical_file_id/values/0",
                            ),
                        ],
                    ),
                    ValidationResultGroup(
                        name="CatdescLength",
                        rule_reference="ISTP-VA-006",
                        severity=Severity.WARNING,
                        results=[
                            ValidationResult(
                                valid=True,
                                reference="",
                                severity=Severity.WARNING,
                                message="length 12 within range",
                                target="variables/B/attributes/CATDESC/values/0",
                            ),
                            ValidationResult(
                                valid=False,
                                reference="",
                                severity=Severity.WARNING,
                                message="length 95 exceeds maximum 80",
                                target="variables/Epoch/attributes/CATDESC/values/0",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    all_issues = flatten(tree)
    assert len(all_issues) == 3

    filtered = filter_issues(all_issues, Verbosity.NORMAL)
    assert len(filtered) == 2
    assert all(not i.passed for i in filtered)

    summary = summary_line(all_issues, "test.cdf", "ISTP")
    assert summary == "test.cdf [ISTP]: 1 error, 1 warning (1 passed)"
```

**Step 2: Run all tests**

Run: `uv run pytest -v`
Expected: PASS

**Step 3: Run lint and type checker**

Run: `make lint`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/test_report_transform.py
git commit -m "test: add end-to-end integration test for report transform pipeline"
```
