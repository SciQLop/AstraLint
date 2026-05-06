from datetime import datetime
from pathlib import Path

from jinja2 import Template

from ..base import Severity, ValidationResult, ValidationResultGroup

_REPORT_CSS = """
        .alr { /* scope all report styles */ }
        .alr {
            --alr-success: var(--color-success, #22c55e);
            --alr-error: var(--color-error, #ef4444);
            --alr-warning: var(--color-warning, #f59e0b);
            --alr-info: var(--color-info, #3b82f6);
            --alr-bg: var(--color-bg, #f8fafc);
            --alr-card: var(--color-card, #ffffff);
            --alr-border: var(--color-border, #e2e8f0);
            --alr-text: var(--color-text, #1e293b);
            --alr-text-muted: var(--color-text-muted, #64748b);
            --alr-group-header: var(--color-group-header, #f1f5f9);
            --alr-group-hover: var(--color-group-hover, #e2e8f0);
            --alr-header-from: var(--color-header-from, #1e293b);
            --alr-header-to: var(--color-header-to, #334155);
            --alr-badge-pass-bg: #dcfce7;
            --alr-badge-pass-fg: #166534;
            --alr-badge-fail-bg: #fee2e2;
            --alr-badge-fail-fg: #991b1b;
            --alr-sev-error-bg: #fee2e2;
            --alr-sev-error-fg: #991b1b;
            --alr-sev-warning-bg: #fef3c7;
            --alr-sev-warning-fg: #92400e;
            --alr-sev-info-bg: #dbeafe;
            --alr-sev-info-fg: #1e40af;
            color: var(--alr-text);
        }

        @media (prefers-color-scheme: dark) {
            .alr {
                --alr-badge-pass-bg: #14532d; --alr-badge-pass-fg: #86efac;
                --alr-badge-fail-bg: #7f1d1d; --alr-badge-fail-fg: #fca5a5;
                --alr-sev-error-bg: #7f1d1d; --alr-sev-error-fg: #fca5a5;
                --alr-sev-warning-bg: #78350f; --alr-sev-warning-fg: #fde68a;
                --alr-sev-info-bg: #1e3a5f; --alr-sev-info-fg: #93c5fd;
            }
        }

        [data-theme="dark"] .alr {
            --alr-badge-pass-bg: #14532d; --alr-badge-pass-fg: #86efac;
            --alr-badge-fail-bg: #7f1d1d; --alr-badge-fail-fg: #fca5a5;
            --alr-sev-error-bg: #7f1d1d; --alr-sev-error-fg: #fca5a5;
            --alr-sev-warning-bg: #78350f; --alr-sev-warning-fg: #fde68a;
            --alr-sev-info-bg: #1e3a5f; --alr-sev-info-fg: #93c5fd;
        }

        [data-theme="light"] .alr {
            --alr-badge-pass-bg: #dcfce7; --alr-badge-pass-fg: #166534;
            --alr-badge-fail-bg: #fee2e2; --alr-badge-fail-fg: #991b1b;
            --alr-sev-error-bg: #fee2e2; --alr-sev-error-fg: #991b1b;
            --alr-sev-warning-bg: #fef3c7; --alr-sev-warning-fg: #92400e;
            --alr-sev-info-bg: #dbeafe; --alr-sev-info-fg: #1e40af;
        }

        .alr .alr-header {
            background: linear-gradient(135deg, var(--alr-header-from) 0%, var(--alr-header-to) 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }

        .alr .alr-header h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
        .alr .alr-header .meta { opacity: 0.8; font-size: 0.875rem; }

        .alr .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .alr .stat {
            background: var(--alr-card);
            border-radius: 8px;
            padding: 1.25rem;
            text-align: center;
            border: 1px solid var(--alr-border);
        }

        .alr .stat .count { font-size: 2rem; font-weight: 700; }
        .alr .stat .label { font-size: 0.75rem; text-transform: uppercase; color: var(--alr-text-muted); }
        .alr .stat.passed .count { color: var(--alr-success); }
        .alr .stat.failed .count { color: var(--alr-error); }
        .alr .stat.warnings .count { color: var(--alr-warning); }

        .alr .results { background: var(--alr-card); border-radius: 12px; border: 1px solid var(--alr-border); }

        .alr .group { border-bottom: 1px solid var(--alr-border); }
        .alr .group:last-child { border-bottom: none; }

        .alr .group-header {
            padding: 1rem 1.5rem;
            background: var(--alr-group-header);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            user-select: none;
        }

        .alr .group-header:hover { background: var(--alr-group-hover); }

        .alr .group-header .arrow {
            transition: transform 0.2s;
            color: var(--alr-text-muted);
        }

        .alr .group.collapsed .arrow { transform: rotate(-90deg); }
        .alr .group.collapsed .group-content { display: none; }

        .alr .group-header .name { font-weight: 600; }
        .alr .group-header .ref { color: var(--alr-text-muted); font-size: 0.875rem; }

        .alr .group-header .badge {
            margin-left: auto;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .alr .badge.pass { background: var(--alr-badge-pass-bg); color: var(--alr-badge-pass-fg); }
        .alr .badge.fail { background: var(--alr-badge-fail-bg); color: var(--alr-badge-fail-fg); }

        .alr .group-content { padding-left: 1.5rem; }

        .alr .result {
            padding: 0.75rem 1.5rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            border-bottom: 1px solid var(--alr-border);
        }

        .alr .result:last-child { border-bottom: none; }

        .alr .result .icon { font-size: 1rem; flex-shrink: 0; margin-top: 0.1rem; }
        .alr .result.valid .icon { color: var(--alr-success); }
        .alr .result.invalid .icon { color: var(--alr-error); }

        .alr .result .content { flex: 1; min-width: 0; }
        .alr .result .message { word-break: break-word; }
        .alr .result .reference { font-weight: 600; color: var(--alr-text); }
        .alr .result .target { font-size: 0.875rem; color: var(--alr-info); font-family: monospace; }

        .alr .severity {
            font-size: 0.625rem;
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
            flex-shrink: 0;
        }

        .alr .severity.ERROR { background: var(--alr-sev-error-bg); color: var(--alr-sev-error-fg); }
        .alr .severity.WARNING { background: var(--alr-sev-warning-bg); color: var(--alr-sev-warning-fg); }
        .alr .severity.INFO { background: var(--alr-sev-info-bg); color: var(--alr-sev-info-fg); }

        .alr footer {
            text-align: center;
            padding: 2rem;
            color: var(--alr-text-muted);
            font-size: 0.875rem;
        }
"""

_REPORT_BODY = """
    <div class="alr">
        <header class="alr-header">
            <h1>🔬 AstraLint Conformance Report</h1>
            <div class="meta">
                <span>Generated: {{ timestamp }}</span>
                {% if suite_name %} · <span>Suite: {{ suite_name }}</span>{% endif %}
            </div>
        </header>

        <div class="summary">
            <div class="stat passed">
                <div class="count">{{ stats.passed }}</div>
                <div class="label">Passed</div>
            </div>
            <div class="stat failed">
                <div class="count">{{ stats.failed }}</div>
                <div class="label">Failed</div>
            </div>
            <div class="stat warnings">
                <div class="count">{{ stats.warnings }}</div>
                <div class="label">Warnings</div>
            </div>
            <div class="stat">
                <div class="count">{{ stats.total }}</div>
                <div class="label">Total</div>
            </div>
        </div>

        <div class="results">
            {{ render_item(results) }}
        </div>

        <footer>
            AstraLint — Space Physics Data Conformance Checker
        </footer>
    </div>

    <script>
        document.querySelectorAll('.group-header').forEach(header => {
            header.addEventListener('click', () => {
                header.parentElement.classList.toggle('collapsed');
            });
        });
    </script>
"""

HTML_TEMPLATE = (
    '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
    '    <meta charset="UTF-8">\n'
    '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    "    <title>AstraLint Report</title>\n"
    "    <style>\n"
    "        * { box-sizing: border-box; margin: 0; padding: 0; }\n"
    "        body {\n"
    "            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n"
    "            background: var(--color-bg, #f8fafc);\n"
    "            color: var(--color-text, #1e293b);\n"
    "            line-height: 1.6;\n"
    "            padding: 2rem;\n"
    "        }\n"
    "        .container { max-width: 1000px; margin: 0 auto; }\n"
    + _REPORT_CSS
    + '    </style>\n</head>\n<body>\n    <div class="container">\n'
    + _REPORT_BODY
    + "    </div>\n</body>\n</html>\n"
)

EMBED_TEMPLATE = "<style>" + _REPORT_CSS + "</style>\n" + _REPORT_BODY

RESULT_TEMPLATE = """
<div class="result {{ 'valid' if result.valid else 'invalid' }}">
    <span class="icon">{{ '✓' if result.valid else '✗' }}</span>
    <div class="content">
        <span class="reference">{{ result.reference }}</span>: 
        <span class="message">{{ result.message }}</span>
        {% if result.target != 'Global' %}
        <div class="target">@ {{ result.target }}</div>
        {% endif %}
    </div>
    <span class="severity {{ result.severity.value }}">{{ result.severity.value }}</span>
</div>
"""

GROUP_TEMPLATE = """
<div class="group">
    <div class="group-header">
        <span class="arrow">▼</span>
        <span class="name">{{ group.name }}</span>
        {% if group.rule_reference %}<span class="ref">[{{ group.rule_reference }}]</span>{% endif %}
        <span class="badge {{ 'pass' if all_valid else 'fail' }}">
            {{ 'PASS' if all_valid else 'FAIL' }}
        </span>
    </div>
    <div class="group-content">
        {% for item in group.results %}
            {{ render_item(item) }}
        {% endfor %}
    </div>
</div>
"""


def _count_stats(item: ValidationResult | ValidationResultGroup) -> dict:
    """Recursively count passed/failed/warnings."""
    stats = {"passed": 0, "failed": 0, "warnings": 0, "total": 0}

    if isinstance(item, ValidationResult):
        stats["total"] = 1
        if item.valid:
            stats["passed"] = 1
        elif item.severity == Severity.WARNING:
            stats["warnings"] = 1
        else:
            stats["failed"] = 1
    elif isinstance(item, ValidationResultGroup):
        for child in item.results:
            child_stats = _count_stats(child)
            for key in stats:
                stats[key] += child_stats[key]

    return stats


def _is_all_valid(item: ValidationResult | ValidationResultGroup) -> bool:
    """Check if all results in an item are valid."""
    if isinstance(item, ValidationResult):
        return item.valid
    return all(_is_all_valid(child) for child in item.results)


def _render_item(item: ValidationResult | ValidationResultGroup) -> str:
    """Render a single item (result or group) to HTML."""
    if isinstance(item, ValidationResult):
        template = Template(RESULT_TEMPLATE)
        return template.render(result=item)
    else:
        template = Template(GROUP_TEMPLATE)
        return template.render(group=item, all_valid=_is_all_valid(item), render_item=_render_item)


def _render_report(template_str: str, results: ValidationResultGroup) -> str:
    template = Template(template_str)
    stats = _count_stats(results)
    return template.render(
        results=results,
        stats=stats,
        suite_name=results.name,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        render_item=_render_item,
    )


def generate_html(results: ValidationResultGroup) -> str:
    """Generate complete standalone HTML report."""
    return _render_report(HTML_TEMPLATE, results)


def generate_html_fragment(results: ValidationResultGroup) -> str:
    """Generate an HTML fragment suitable for embedding in an existing page."""
    return _render_report(EMBED_TEMPLATE, results)


def report(results: ValidationResultGroup, dest: Path | None = None):
    """Generate and optionally save an HTML report."""
    html_content = generate_html(results)

    if dest:
        dest.write_text(html_content)
        print(f"HTML report saved to: {dest}")
    else:
        print(html_content)
