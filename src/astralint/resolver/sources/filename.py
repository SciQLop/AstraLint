import re

from ...base.file import File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

# ISTP filename stem: <logical_source>_<YYYYMMDD>[_vN]. logical_source is greedy
# so the trailing date (and optional version) anchor the match.
_STEM_RE = re.compile(r"^(?P<logical_source>[a-z0-9_-]+)_(?P<date>\d{8})(?:_v(?P<version>\d+))?$")


def _stem(filename: str) -> str:
    return filename[:-4] if filename.lower().endswith(".cdf") else filename


def _match(file: File) -> re.Match | None:
    return _STEM_RE.match(_stem(file.filename))


def logical_file_id_from_filename(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if _match(file) is None:
        return None
    return ResolverOutput(
        value=_stem(file.filename),
        provenance_note=f"derived from filename '{file.filename}'",
    )


def logical_source_from_filename(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    match = _match(file)
    if match is None:
        return None
    return ResolverOutput(
        value=match.group("logical_source"),
        provenance_note=f"derived from filename '{file.filename}'",
    )


def data_version_from_filename(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    match = _match(file)
    if match is None or match.group("version") is None:
        return None
    return ResolverOutput(
        value=match.group("version"),
        provenance_note=f"version from filename '{file.filename}'",
    )
