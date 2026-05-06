from pathlib import Path

from cyclopts import App
from rich.console import Console, Group
from rich.panel import Panel
from rich.pretty import Pretty

from .base import (
    ConformanceSuite,
    Severity,
    ValidationResultGroup,
    get_suite,
    list_all_suites,
    load_file,
)
from .base.conformance_suite import load_extra_rules
from .config import (
    find_config_file,
    find_project_root,
    load_config,
    validate_config_file,
)
from .config.loader import generate_starter_config
from .config.paths import expand_lint_paths
from .reports import report

app = App()
config_app = App(name="config", help="Manage AstraLint configuration.")
app.command(config_app)


@config_app.command()
def validate(path: Path | None = None):
    """Validate a configuration file for errors.

    Parameters
    ----------
    path : Path, optional
        Path to config file. Auto-detects if not provided.
    """
    console = Console()

    config_path = path or find_config_file()
    if not config_path:
        console.print("[yellow]No configuration file found.[/]")
        console.print(f"Searched in: {find_project_root()}")
        console.print("\nRun [bold]astralint config init[/] to create one.")
        raise SystemExit(1)

    is_valid, error = validate_config_file(config_path)
    if is_valid:
        console.print(f"[green]✓[/] [bold]{config_path}[/] is valid")
    else:
        console.print(f"[red]✗[/] [bold]{config_path}[/] has errors:")
        console.print(f"  {error}")
        raise SystemExit(1)


@config_app.command()
def show(path: Path | None = None):
    """Display the resolved configuration.

    Shows the merged configuration from all sources (pyproject.toml,
    .astralint.yaml, etc.) with their final values.

    Parameters
    ----------
    path : Path, optional
        Path to specific config file to use.
    """
    console = Console()

    cfg = load_config(config_file=path)

    # Show which config files were loaded
    root = find_project_root()
    sources = []
    if (root / "pyproject.toml").exists():
        sources.append("pyproject.toml")
    yaml_config = find_config_file(root)
    if yaml_config:
        sources.append(str(yaml_config.name))

    if sources:
        console.print(f"[dim]Config sources: {', '.join(sources)}[/]\n")
    else:
        console.print("[dim]No config files found, using defaults[/]\n")

    console.print(
        Panel(
            Pretty(cfg.model_dump()), title="[bold]Resolved Configuration[/]", border_style="blue"
        )
    )


@config_app.command()
def init(force: bool = False):
    """Generate a starter .astralint.yaml configuration file.

    Parameters
    ----------
    force : bool
        Overwrite existing config file if present.
    """
    console = Console()

    root = find_project_root()
    config_path = root / ".astralint.yaml"

    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists:[/] {config_path}")
        console.print("Use [bold]--force[/] to overwrite.")
        raise SystemExit(1)

    config_path.write_text(generate_starter_config())
    console.print(f"[green]✓[/] Created [bold]{config_path}[/]")
    console.print("\nEdit this file to customize AstraLint behavior.")


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
    show_passed: bool | None = None,
    strict: bool = False,
):
    """Lint the given file or directory against the specified conformance suite.

    Parameters
    ----------
    path : str
        The path to the file or directory to lint.
    suite : str, optional
        The name of the conformance suite to use for linting. Overrides config file.
    select : list[str], optional
        Rule patterns to include in linting. Overrides config file.
    ignore : list[str], optional
        Rule patterns to exclude from linting. Overrides config file.
    config_file : Path, optional
        Path to specific config file to use.
    output : str, optional
        Output format: console, html, json. Overrides config file.
    dest : Path, optional
        Destination file path for the report.
    verbose : bool
        Show detailed output including config file used.
    show_passed : bool, optional
        Show passed assertions in the report. Overrides config file.
    strict : bool
        Exit with error code on warnings too, not just errors.
    """
    console = Console()

    # Build CLI overrides
    cli_overrides: dict = {}
    if suite:
        cli_overrides["suite"] = suite
    if select:
        cli_overrides["select"] = select
    if ignore:
        cli_overrides["ignore"] = ignore
    if output or dest or verbose or show_passed is not None:
        cli_overrides["output"] = {}
        if output:
            cli_overrides["output"]["format"] = output
        if dest:
            cli_overrides["output"]["dest"] = dest
        if verbose:
            cli_overrides["output"]["verbose"] = True
        if show_passed is not None:
            cli_overrides["output"]["show_passed"] = show_passed

    # Load merged config
    cfg = load_config(
        config_file=config_file, cli_overrides=cli_overrides if cli_overrides else None
    )

    if cfg.output.verbose:
        yaml_config = find_config_file()
        if yaml_config:
            console.print(f"[dim]Using config: {yaml_config}[/]")
        console.print(f"[dim]Suite: {cfg.suite}[/]")
        if cfg.select:
            console.print(f"[dim]Select: {cfg.select}[/]")
        if cfg.ignore:
            console.print(f"[dim]Ignore: {cfg.ignore}[/]")
        console.print()

    # Load any extra rule directories before constructing the suite
    if cfg.extra_rules:
        project_root = find_project_root()
        load_extra_rules([p if p.is_absolute() else project_root / p for p in cfg.extra_rules])

    # Expand directories using cfg.include/exclude glob patterns
    files_to_lint = expand_lint_paths(path, include=cfg.include, exclude=cfg.exclude)

    # Run linting
    checker: ConformanceSuite | None = get_suite(cfg.suite)
    if checker:
        results = []
        for p in files_to_lint:
            if file := load_file(str(p)):
                results.append(
                    checker.run(
                        file,
                        select=cfg.select or None,
                        ignore=cfg.ignore or None,
                        severity_overrides=cfg.severity_overrides or None,
                    )
                )

        results = ValidationResultGroup(
            name="AstraLint Results", rule_reference="", results=results, severity=Severity.INFO
        )
        report(
            results,
            output=cfg.output.format,
            dest=cfg.output.dest,
            show_passed=cfg.output.show_passed,
        )

        # Exit with error code if validation failed
        if results.has_errors():
            raise SystemExit(1)
        elif strict and results.has_failures():
            raise SystemExit(1)
    else:
        raise ValueError(
            f"Unknown conformance suite '{cfg.suite}'. "
            f"Available suites: {', '.join(list_all_suites())}"
        )


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
            suites_panels.append(
                Panel(Group(f"[bold]{s.name}[/bold]", s.description, f"url: {s.url}"), title=suite)
            )

    console.print(Panel(Group(*suites_panels), title="Available Conformance Suites"))


@app.command()
def dump_file_model(path: str):
    """Dump the internal file model for a given file, showing how AstraLint parses it.

    Parameters
    ----------
    path : str
        The path to the file to dump.
    """
    console = Console()

    if file := load_file(path):
        console.print(Panel(Pretty(file), title=f"Internal File Model for {path}"))
    else:
        console.print(f"[red]✗[/] Could not load file: {path}")


def main():
    app()


if __name__ == "__main__":
    main()
