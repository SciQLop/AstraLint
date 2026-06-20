from ...base.file import File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput


def needs_user_input(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    """Flag an irreducible attribute — physical units, identity/provenance, prose,
    or an external identifier — as requiring human input. Carries no value: these
    are never auto-filled, only surfaced so nothing is silently unaddressable."""
    return ResolverOutput(
        value=None,
        provenance_note=f"{attribute} must be provided by a human (never auto-filled)",
    )
