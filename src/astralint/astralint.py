from cyclopts import App
from pathlib import Path
from rich.console import Console, Group
from rich.panel import Panel

from .base import *
from .reports import report

app = App()


@app.command()
def lint(path: str, suite: str = "ISTP", select: list[str] | None = None, ignore: list[str] | None = None,
         output: str = "console", dest: Path | None = None):
    """Lint the given file or directory against the specified conformance suite.

    Parameters
    ----------
    path : str
        The path to the file or directory to lint.
    suite : str, optional
        The name of the conformance suite to use for linting. Default is "ISTP".
    select : Optional[list[str]], optional
        A list of rule names to include in the linting process. If not provided, all rules in the suite will be used.
    ignore : Optional[list[str]], optional
        A list of rule names to exclude from the linting process. If not provided, no rules will be excluded.
    output: str, optional
        The output format for the report. Default is "console". Other options may include "html", "json", etc.
    dest : str, optional
        The destination file path for the report. If not provided, the report will not be saved to a file.
    """
    checker: ConformanceSuite | None = get_suite(suite)
    if checker:
        if file := load_file(path):
            results = checker.run(file, select=select, ignore=ignore)
            report(results, output=output, dest=dest)
    else:
        raise ValueError(f"Unknown conformance suite '{suite}'. Available suites: {', '.join(list_all_suites())}")


@app.command()
def list_suites(details: bool = False):
    """List all available conformance suites.

    Parameters
    ----------
    details : bool, optional
        If True, display detailed information about each suite. Default is False.
    """
    console = Console()
    suites = list_all_suites()
    suites_panels = []
    for suite in suites:
        s = get_suite(suite)
        if s:
            suites_panels.append(Panel(Group(
                f"[bold]{s.name}[/bold]",
                s.description,
                f"url: {s.url}"
            ), title=suite))

    console.print(Panel(Group(*suites_panels), title="Available Conformance Suites"))


if __name__ == "__main__":
    app()
