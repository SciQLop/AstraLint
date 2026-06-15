import re
from functools import singledispatch
from pathlib import Path

from rich.console import Console, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from ..base import Severity, ValidationResult, ValidationResultGroup

_SEVERITY_COLOR = {
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "blue",
    Severity.SKIPPED: "dim",
}
_SEVERITY_RANK = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2, Severity.SKIPPED: 3}
_FILE_NAME_RE = re.compile(r"on file '(?P<name>.+)'")


@singledispatch
def _render(obj) -> RenderableType:
    raise ValueError(
        f"Cannot render object of type {type(obj)}. Expected ValidationResult or ValidationResultGroup."
    )


@_render.register(ValidationResult)
def _render_result(res: ValidationResult) -> Text:
    """Renders a single leaf (ValidationResult)."""
    icon = "[bold green]✔[/]" if res.valid else "[bold red]✘[/]"

    # Severity color mapping
    color = (
        "red"
        if res.severity == Severity.ERROR
        else "yellow"
        if res.severity == Severity.WARNING
        else "blue"
    )

    text = Text.from_markup(f"{icon} [bold]{res.reference}[/]: {escape(res.message)}")

    # Severity only muddies passing lines; surface it only when the check failed (#11).
    if not res.valid:
        text.append(f" ({res.severity.value})", style=f"bold {color}")

    # Show target if it's not the generic 'Global'
    if res.target != "Global":
        text.append(f" @ {res.target}", style="italic cyan")

    return text


@_render.register(ValidationResultGroup)
def _render_group(group: ValidationResultGroup) -> Tree:
    """Renders a branch (ValidationResultGroup) and recurses."""
    # Logic for group header style based on validity
    all_valid = all(getattr(r, "valid", True) for r in group.results)
    header_style = "bold green" if all_valid else "bold yellow"

    header = Text.assemble(
        (f" {group.name} ", header_style), (f"[{group.rule_reference}]", "italic dim")
    )
    if group.url:
        header.append("\n  ↳ ", style="dim")
        header.append(group.url, style=f"dim link {group.url}")

    tree = Tree(header)
    for item in group.results:
        # This recursive call handles the nesting automatically
        tree.add(_render(item))
    return tree


def console_report(results: ValidationResultGroup, console: Console):
    """Helper function to print the report to a given Console instance."""
    report_tree = _render(results)
    console.print("\n")
    console.print(
        Panel(
            report_tree,
            title="[bold]AstraLint Conformance Report[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    return console


def _collect_findings(
    node: ValidationResult | ValidationResultGroup, code: str, url: str
) -> list[tuple[ValidationResult, str, str]]:
    """Flatten the tree into (leaf, rule_code, doc_url), carrying the nearest rule's code/url."""
    if isinstance(node, ValidationResult):
        return [(node, node.reference or code, url)]
    code = node.rule_reference or code
    url = node.url or url
    findings: list[tuple[ValidationResult, str, str]] = []
    for child in node.results:
        findings.extend(_collect_findings(child, code, url))
    return findings


def _file_sections(
    results: ValidationResultGroup,
) -> list[tuple[str | None, ValidationResultGroup]]:
    """Split the top result group into per-file sections, falling back to a single section."""
    file_groups = [
        child
        for child in results.results
        if isinstance(child, ValidationResultGroup) and "on file '" in child.name
    ]
    if not file_groups:
        return [(None, results)]
    sections = []
    for group in file_groups:
        match = _FILE_NAME_RE.search(group.name)
        sections.append((match.group("name") if match else group.name, group))
    return sections


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _summary_text(counts: dict[str, int]) -> Text:
    problems = counts["ERROR"] + counts["WARNING"]
    info = counts["INFO"]
    if problems == 0:
        if info == 0:
            return Text("✓ All checks passed", style="bold green")
        return Text(
            f"✓ No errors or warnings ({_plural(info, 'info finding')})", style="bold green"
        )
    parts = [
        _plural(counts[sev], label)
        for sev, label in (("ERROR", "error"), ("WARNING", "warning"))
        if counts[sev] > 0
    ]
    text = Text(f"✗ Found {_plural(problems, 'problem')} ({', '.join(parts)})", style="bold red")
    if info:
        text.append(f", plus {_plural(info, 'info finding')}", style="blue")
    return text


def _render_finding(leaf: ValidationResult, code: str) -> Text:
    color = _SEVERITY_COLOR.get(leaf.severity, "white")
    text = Text(f"  {leaf.severity.value:<8}", style=f"bold {color}")
    text.append(f"{code}  ", style="dim")
    if leaf.target and leaf.target != "Global":
        text.append(f"{leaf.target} › ", style="cyan")
    text.append(escape(leaf.message))
    return text


_LISTED_SEVERITIES = (Severity.ERROR, Severity.WARNING)


def _render_quiet(results: ValidationResultGroup, console: Console):
    """Linter-style output: a flat, severity-sorted list of errors and warnings plus a verdict.

    INFO findings are kept out of the list (surfaced as a count in the verdict) so the
    default view stays focused on what needs action; ``--show-passed`` shows everything.
    """
    console.print()
    for filename, group in _file_sections(results):
        failures = [
            (leaf, code)
            for leaf, code, _ in _collect_findings(group, "", "")
            if not leaf.valid and leaf.severity in _LISTED_SEVERITIES
        ]
        if not failures:
            continue
        failures.sort(key=lambda f: _SEVERITY_RANK.get(f[0].severity, 99))
        if filename:
            console.print(Text(filename, style="bold underline"))
        for leaf, code in failures:
            console.print(_render_finding(leaf, code))
        console.print()

    counts = results.count_by_severity()
    if counts["INFO"]:
        console.print(
            Text(
                f"  {counts['INFO']} info finding(s) hidden — use --show-passed "
                "or --output html to see them",
                style="dim",
            )
        )
    console.print(_summary_text(counts))


def report(
    results: ValidationResultGroup,
    dest: Path | None = None,
    show_passed: bool | None = None,
    failed_only: bool = False,
):
    """The main entry point called by the CLI.

    Quiet by default (failures + verdict, linter-style). ``show_passed=True``
    restores the full nested tree.
    """
    console = Console()
    if show_passed:
        console_report(results, console)
        console.print(_summary_text(results.count_by_severity()))
    else:
        _render_quiet(results, console)
