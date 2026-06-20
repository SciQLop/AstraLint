from ...base.file import DataType, File, Variable
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

_TIME_TYPES = (DataType.TT2000, DataType.CDFEPOCH, DataType.CDFEPOCH16)
_NUMERIC_TYPES = (
    DataType.INT8,
    DataType.INT16,
    DataType.INT32,
    DataType.INT64,
    DataType.UINT8,
    DataType.UINT16,
    DataType.UINT32,
    DataType.UINT64,
    DataType.FLOAT32,
    DataType.FLOAT64,
)
_DEPEND_ATTRS = ("DEPEND_0", "DEPEND_1", "DEPEND_2", "DEPEND_3")
_LABL_ATTRS = ("LABL_PTR_1", "LABL_PTR_2", "LABL_PTR_3")


def _record_count(var: Variable) -> int:
    return var.shape[0] if var.shape else 0


def _attr_scalar(var: Variable, name: str) -> object:
    attr = var.attributes.get(name)
    if attr and attr.values:
        return attr.values[0]
    return None


def _is_pointed_by(file: File, target: str, attr_names: tuple[str, ...]) -> bool:
    return any(
        _attr_scalar(var, name) == target for var in file.variables.values() for name in attr_names
    )


def depend0_finder(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    var = file.variables[variable]
    if not var.record_variance:
        return None
    n = _record_count(var)
    candidates = [
        name
        for name, tv in file.variables.items()
        if tv.data_type in _TIME_TYPES
        and _record_count(tv) == n
        and _attr_scalar(tv, "VAR_TYPE") == "support_data"
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return ResolverOutput(
            value=candidates[0],
            provenance_note=f"unique time variable with matching record count ({n})",
        )
    return ResolverOutput(
        value=candidates[0],
        ambiguous=True,
        alternatives=candidates,
        provenance_note=f"{len(candidates)} candidate time variables; needs a human choice",
    )


def var_type_infer(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    if _is_pointed_by(file, variable, _DEPEND_ATTRS):
        return ResolverOutput(
            value="support_data", provenance_note="referenced by a DEPEND_i pointer"
        )
    if _is_pointed_by(file, variable, _LABL_ATTRS):
        return ResolverOutput(
            value="metadata", provenance_note="referenced by a LABL_PTR_i pointer"
        )
    var = file.variables[variable]
    if var.data_type in _NUMERIC_TYPES and "DEPEND_0" in var.attributes:
        return ResolverOutput(
            value="data", provenance_note="numeric variable with its own DEPEND_0"
        )
    return None


def display_type_infer(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    var = file.variables[variable]
    if not var.record_variance:
        return None
    ndim = len(var.shape)  # shape[0] is the record dimension
    if ndim == 1:
        return ResolverOutput(value="time_series", provenance_note="1-D record-varying variable")
    if ndim == 2 and "DEPEND_1" in var.attributes:
        return ResolverOutput(value="spectrogram", provenance_note="2-D variable with DEPEND_1")
    return None
