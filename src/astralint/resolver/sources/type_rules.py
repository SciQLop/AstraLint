from typing import Any

from ...base.file import DataType, File
from ...base.validation_result import ValidationResult
from ..models import ResolverOutput

# ISTP default fill values keyed on the abstract CDF data type. Unsigned types
# are intentionally omitted in Phase 1 (no agreed ISTP default here yet).
_FILLVAL_BY_TYPE: dict[DataType, Any] = {
    DataType.INT8: -128,
    DataType.INT16: -32768,
    DataType.INT32: -(2**31),
    DataType.INT64: -(2**63),
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


def scaletyp_default(
    file: File, variable: str | None, attribute: str, failure: ValidationResult | None
) -> ResolverOutput | None:
    if variable is None or variable not in file.variables:
        return None
    return ResolverOutput(value="linear", provenance_note="ISTP default SCALETYP")


# Phase-1b (needs variable data, not carried by the File model): FORMAT from
# observed magnitude, MONOTON from the epoch array, SCALEMIN/SCALEMAX from
# percentiles. Left unimplemented on purpose so the catalog gap is visible.
