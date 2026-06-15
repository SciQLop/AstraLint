from .console import report as console_report
from .html import report as html_report
from .json import report as json_report

_REPORTERS = {
    "console": console_report,
    "html": html_report,
    "json": json_report,
}


def report(
    results, output="console", dest=None, show_passed: bool | None = None, failed_only: bool = False
):
    """The main entry point called by the CLI.

    Console output is quiet by default (failures + verdict) and computes its
    verdict from the full results, so filtering is delegated to it. HTML and
    JSON stay comprehensive unless explicitly narrowed.
    """
    if output == "console":
        return console_report(results, dest, show_passed=show_passed, failed_only=failed_only)

    reporter = _REPORTERS.get(output)
    if reporter is None:
        raise ValueError(
            f"Unknown output format '{output}'. Supported formats: {', '.join(sorted(_REPORTERS))}."
        )
    if failed_only:
        results = results.failures_only()
    elif show_passed is False:
        results = results.without_passed()
    return reporter(results, dest)
