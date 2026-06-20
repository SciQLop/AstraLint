import numpy as np
import pycdfpp

from ..base.file import DataType
from .models import Fix, Scope

# Abstract data type -> (numpy dtype, pycdfpp CDF type) for writing numeric values.
_CDF_WRITE = {
    DataType.INT8: (np.int8, pycdfpp.DataType.CDF_INT1),
    DataType.INT16: (np.int16, pycdfpp.DataType.CDF_INT2),
    DataType.INT32: (np.int32, pycdfpp.DataType.CDF_INT4),
    DataType.INT64: (np.int64, pycdfpp.DataType.CDF_INT8),
    DataType.FLOAT32: (np.float32, pycdfpp.DataType.CDF_FLOAT),
    DataType.FLOAT64: (np.float64, pycdfpp.DataType.CDF_DOUBLE),
    DataType.TT2000: (np.int64, pycdfpp.DataType.CDF_TIME_TT2000),
}


def _numeric_value_and_type(variable_abstract_type: DataType, value: object):
    # CDF_EPOCH16 fill is a 2-component (real, imaginary) time, written as a
    # complex128. fillval_by_type returns it as a (real, imaginary) tuple.
    if isinstance(value, tuple):
        real, imag = value
        return np.array([complex(real, imag)], dtype=np.complex128), pycdfpp.DataType.CDF_EPOCH16
    # Python float -> always write as FLOAT64 (e.g. standard -1e31 fill value);
    # Python int -> use the variable's native CDF type.
    if isinstance(value, float):
        return np.array([value], dtype=np.float64), pycdfpp.DataType.CDF_DOUBLE
    np_dtype, cdf_type = _CDF_WRITE[variable_abstract_type]
    return np.array([value], dtype=np_dtype), cdf_type


def _abstract_type(var) -> DataType:
    # reuse the codec mapping so apply and load agree on types
    from ..codecs.cdf import _to_data_type

    return _to_data_type(var.type)


def _apply_one(cdf, fix: Fix) -> None:
    if fix.scope == Scope.GLOBAL:
        # Phase 1 emits no global fixes, but keep the path honest.
        if fix.action == "add":
            cdf.add_attribute(fix.attribute, [[fix.value]], [pycdfpp.DataType.CDF_CHAR])
        return

    # Re-fetch the variable handle every time: pycdfpp wrappers hold references
    # into C++ containers and are invalidated by any structural add/remove.
    var = cdf[fix.variable]
    is_string = isinstance(fix.value, str)

    if fix.action == "add":
        if is_string:
            var.add_attribute(fix.attribute, fix.value)
        else:
            values, cdf_type = _numeric_value_and_type(_abstract_type(var), fix.value)
            var.add_attribute(fix.attribute, values, cdf_type)
    else:  # set
        attr = var.attributes[fix.attribute]
        if is_string:
            attr.set_value(fix.value)
        else:
            values, cdf_type = _numeric_value_and_type(_abstract_type(var), fix.value)
            attr.set_value(values, cdf_type)


def apply_fixes(cdf_bytes: bytes, fixes: list[Fix]) -> bytes:
    cdf = pycdfpp.load(cdf_bytes)
    for fix in fixes:
        _apply_one(cdf, fix)
    return bytes(pycdfpp.save(cdf))
