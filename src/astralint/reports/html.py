from datetime import datetime
from pathlib import Path

from jinja2 import Template

from ..base import Severity, ValidationResult, ValidationResultGroup

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AstraLint Report</title>
    <style>
        :root {
            --color-success: #22c55e;
            --color-error: #ef4444;
            --color-warning: #f59e0b;
            --color-info: #3b82f6;
            --color-bg: #f8fafc;
            --color-card: #ffffff;
            --color-border: #e2e8f0;
            --color-text: #1e293b;
            --color-text-muted: #64748b;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
            padding: 2rem;
        }
        
        .container { max-width: 1000px; margin: 0 auto; }
        
        header {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }
        
        header h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
        header .meta { opacity: 0.8; font-size: 0.875rem; }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat {
            background: var(--color-card);
            border-radius: 8px;
            padding: 1.25rem;
            text-align: center;
            border: 1px solid var(--color-border);
        }
        
        .stat .count { font-size: 2rem; font-weight: 700; }
        .stat .label { font-size: 0.75rem; text-transform: uppercase; color: var(--color-text-muted); }
        .stat.passed .count { color: var(--color-success); }
        .stat.failed .count { color: var(--color-error); }
        .stat.warnings .count { color: var(--color-warning); }
        
        .results { background: var(--color-card); border-radius: 12px; border: 1px solid var(--color-border); }
        
        .group {
            border-bottom: 1px solid var(--color-border);
        }
        
        .group:last-child { border-bottom: none; }
        
        .group-header {
            padding: 1rem 1.5rem;
            background: #f1f5f9;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            user-select: none;
        }
        
        .group-header:hover { background: #e2e8f0; }
        
        .group-header .arrow {
            transition: transform 0.2s;
            color: var(--color-text-muted);
        }
        
        .group.collapsed .arrow { transform: rotate(-90deg); }
        .group.collapsed .group-content { display: none; }
        
        .group-header .name { font-weight: 600; }
        .group-header .ref { color: var(--color-text-muted); font-size: 0.875rem; }
        
        .group-header .badge {
            margin-left: auto;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .badge.pass { background: #dcfce7; color: #166534; }
        .badge.fail { background: #fee2e2; color: #991b1b; }
        
        .group-content { padding-left: 1.5rem; }
        
        .result {
            padding: 0.75rem 1.5rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            border-bottom: 1px solid var(--color-border);
        }
        
        .result:last-child { border-bottom: none; }
        
        .result .icon { font-size: 1rem; flex-shrink: 0; margin-top: 0.1rem; }
        .result.valid .icon { color: var(--color-success); }
        .result.invalid .icon { color: var(--color-error); }
        
        .result .content { flex: 1; min-width: 0; }
        .result .message { word-break: break-word; }
        .result .reference { font-weight: 600; color: var(--color-text); }
        .result .target { font-size: 0.875rem; color: var(--color-info); font-family: monospace; }
        
        .severity {
            font-size: 0.625rem;
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
            flex-shrink: 0;
        }
        
        .severity.ERROR { background: #fee2e2; color: #991b1b; }
        .severity.WARNING { background: #fef3c7; color: #92400e; }
        .severity.INFO { background: #dbeafe; color: #1e40af; }
        
        footer {
            text-align: center;
            padding: 2rem;
            color: var(--color-text-muted);
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
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
</body>
</html>
"""

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


def generate_html(results: ValidationResultGroup) -> str:
    """Generate complete HTML report from validation results."""
    template = Template(HTML_TEMPLATE)
    stats = _count_stats(results)

    return template.render(
        results=results,
        stats=stats,
        suite_name=results.name,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        render_item=_render_item,
    )


def report(results: ValidationResultGroup, dest: Path | None = None):
    """Generate and optionally save an HTML report."""
    html_content = generate_html(results)

    if dest:
        dest.write_text(html_content)
        print(f"HTML report saved to: {dest}")
    else:
        print(html_content)
