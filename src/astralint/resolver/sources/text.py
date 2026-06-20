from ...base.file import File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

# ISTP hard length limits per descriptive attribute.
_MAX_LENGTH = {"CATDESC": 120, "FIELDNAM": 50, "LABLAXIS": 20}


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
