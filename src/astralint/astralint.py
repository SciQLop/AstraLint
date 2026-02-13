from cyclopts import App
from typing import Optional
from .base import *
from .codecs import load_file
from .reports.console import report


app = App()


@app.command()
def lint(path: str, suite: str = "ISTP"):
    """Lint the given file or directory."""
    checker: Optional[ConformanceSuite] = get_suite(suite)
    if checker:
        if file:= load_file(path):
            results = checker.validate(file)
            report(results)
    else:
        raise ValueError(f"Unknown conformance suite '{suite}'. Available suites: {', '.join(list_suites())}")


if __name__ == "__main__":
    app()
