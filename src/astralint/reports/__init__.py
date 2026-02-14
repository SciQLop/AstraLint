from .console import report as console_report
from .html import report as html_report


def report(results, output="console", dest=None):
    """The main entry point called by the CLI."""
    if output == "console":
        return console_report(results, dest)
    elif output == "html":
        return html_report(results, dest)
    else:
        raise ValueError(f"Unknown output format '{output}'. Supported formats: 'console', 'html'.")
