from .console import report as console_report
from .html import report as html_report
from .json import report as json_report

_REPORTERS = {
    "console": console_report,
    "html": html_report,
    "json": json_report,
}


def report(
    results, output="console", dest=None, show_passed: bool = True, failed_only: bool = False
):
    """The main entry point called by the CLI."""
    if failed_only:
        results = results.failures_only()
    elif not show_passed:
        results = results.without_passed()
    reporter = _REPORTERS.get(output)
    if reporter is None:
        raise ValueError(
            f"Unknown output format '{output}'. Supported formats: {', '.join(sorted(_REPORTERS))}."
        )
    return reporter(results, dest)
