from datetime import datetime

from ...base.file import File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

# ISTP hard length limits per descriptive attribute.
_MAX_LENGTH = {"CATDESC": 120, "FIELDNAM": 50, "LABLAXIS": 20}

# Common date formats a Generation_date might use instead of the ISTP yyyymmdd.
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S")


def _parse_date(raw: str) -> datetime | None:
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)  # assorted ISO-8601 variants
    except ValueError:
        return None


def generation_date_format(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    """ISTP-GA-015: Generation_date must be yyyymmdd. Reformat a present, parseable
    date losslessly (same date, ISTP format). Returns None when it is absent or
    not parseable (no fabrication)."""
    attr = file.attributes.get("Generation_date")
    if attr is None or not attr.values or not isinstance(attr.values[0], str):
        return None
    parsed = _parse_date(attr.values[0])
    if parsed is None:
        return None
    return ResolverOutput(
        value=parsed.strftime("%Y%m%d"),
        provenance_note="reformatted Generation_date to the ISTP yyyymmdd format",
    )


def truncate_to_limit(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    """ISTP-VA-020/021/022: an over-long descriptive attribute. Propose the value
    truncated to the hard limit. Always STAGED — truncation is lossy (it can cut
    mid-word and drop meaning), so it is a starting point for a human, never an
    auto-fix."""
    limit = _MAX_LENGTH.get(attribute)
    if limit is None or variable is None or variable not in file.variables:
        return None
    attr = file.variables[variable].attributes.get(attribute)
    if attr is None or not attr.values:
        return None
    current = attr.values[0]
    if not isinstance(current, str) or len(current) <= limit:
        return None
    return ResolverOutput(
        value=current[:limit],
        provenance_note=f"truncated to the {limit}-char limit; review (text was shortened)",
    )
