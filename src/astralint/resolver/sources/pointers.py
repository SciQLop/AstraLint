import difflib

from ...base.file import File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput


def dangling_pointer_suggestion(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    attr = file.variables[variable].attributes.get(attribute)
    if attr is None or not attr.values:
        return None
    referenced = attr.values[0]
    if referenced in file.variables:
        return None  # not dangling
    matches = difflib.get_close_matches(
        str(referenced), list(file.variables.keys()), n=1, cutoff=0.6
    )
    if not matches:
        return None
    return ResolverOutput(
        value=matches[0],
        ambiguous=True,  # Tier 3 is never auto-applied; always staged
        alternatives=matches,
        provenance_note=f"'{referenced}' not found; closest variable name is '{matches[0]}'",
    )
