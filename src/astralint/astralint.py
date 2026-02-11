from cyclopts import App
from .base import *
from .ISTP import ISTP
from rich.console import Console
from rich.table import Table


def report(results: list[ValidationResult]):
    console = Console()
    table = Table(title="ISTP Conformance Report")
    table.add_column("Result")
    table.add_column("ID", style="cyan")
    table.add_column("Severity")
    table.add_column("Message")

    for r in results:
        if r.valid:
            table.add_row(":white_heavy_check_mark:", r.reference, f"[green]{r.severity.name}[/]", r.message)
        else:
            color = "red" if r.severity == Severity.ERROR else "yellow"
            table.add_row(":cross_mark:", r.reference, f"[{color}]{r.severity.name}[/]", r.message)
    console.print(table)


app = App()


@app.command()
def lint(path: str):
    """Lint the given file or directory."""
    istp: ConformanceSuite = ISTP()
    results = istp.validate(path)
    report(results)


if __name__ == "__main__":
    app()
