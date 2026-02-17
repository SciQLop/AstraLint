from functools import singledispatch
from pathlib import Path

from rich.console import Console, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from ..base import Severity, ValidationResult, ValidationResultGroup


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


def report(results: ValidationResultGroup, dest: Path | None = None):
    """The main entry point called by the CLI."""
    console = Console()
    console_report(results, console)
