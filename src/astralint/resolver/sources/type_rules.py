from typing import Any

from ...base.file import DataType, File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

# ISTP/CDAWeb default fill values keyed on the abstract CDF data type. Unsigned
# integers use the maximum value (all bits set), the conventional unsigned fill.
_FILLVAL_BY_TYPE: dict[DataType, Any] = {
    DataType.INT8: -128,
    DataType.INT16: -32768,
    DataType.INT32: -(2**31),
    DataType.INT64: -(2**63),
    DataType.UINT8: 2**8 - 1,
    DataType.UINT16: 2**16 - 1,
    DataType.UINT32: 2**32 - 1,
    DataType.TT2000: -(2**63),
    DataType.FLOAT32: -1e31,
    DataType.FLOAT64: -1e31,
    DataType.CDFEPOCH: -1e31,
    DataType.CDFEPOCH16: (-1e31, -1e31),
    DataType.CHAR: " ",
}


def fillval_by_type(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    data_type = file.variables[variable].data_type
    if data_type not in _FILLVAL_BY_TYPE:
        return None
    return ResolverOutput(
        value=_FILLVAL_BY_TYPE[data_type],
        provenance_note=f"ISTP default FILLVAL for {data_type.value}",
    )


def _scalar(attr: Any) -> Any:
    """Unwrap a (possibly nested, e.g. [[0.0]]) attribute value to its scalar."""
    if attr is None or not attr.values:
        return None
    value = attr.values[0]
    while isinstance(value, (list, tuple)) and value:
        value = value[0]
    return value


def _as_stored(value: Any, data_type: DataType) -> Any:
    """The value as it will actually be written to the variable, so the range
    check matches the stored bits. FLOAT32 quantization can move the -1e31 default
    onto a VALIDMIN that is itself float32(-1e31) — looking outside in double
    precision while landing exactly on the boundary once stored."""
    if data_type == DataType.FLOAT32:
        import numpy as np

        return float(np.float32(value))
    return value


def fillval_outside_range(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    """ISTP-VA-019: FILLVAL must be outside [VALIDMIN, VALIDMAX]. Propose the
    type-standard fill ONLY when it is actually outside the variable's range — the
    default is not outside for every range (e.g. one spanning +/-1e32), and an
    in-range fill would not clear the error. Returns None otherwise."""
    if variable is None or variable not in file.variables:
        return None
    var = file.variables[variable]
    default = _FILLVAL_BY_TYPE.get(var.data_type)
    if default is None:
        return None
    vmin = _scalar(var.attributes.get("VALIDMIN"))
    vmax = _scalar(var.attributes.get("VALIDMAX"))
    if vmin is None or vmax is None:
        return None
    stored = _as_stored(default, var.data_type)
    try:
        outside = stored < vmin or stored > vmax
    except TypeError:
        return None  # non-order-comparable (e.g. an epoch16 tuple fill)
    if not outside:
        return None
    return ResolverOutput(
        value=default,
        provenance_note=f"ISTP default fill for {var.data_type.value}, outside [VALIDMIN, VALIDMAX]",
    )


def scaletyp_default(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    return ResolverOutput(value="linear", provenance_note="ISTP default SCALETYP")


# Phase-1b (needs variable data, not carried by the File model): FORMAT from
# observed magnitude, MONOTON from the epoch array, SCALEMIN/SCALEMAX from
# percentiles. Left unimplemented on purpose so the catalog gap is visible.
