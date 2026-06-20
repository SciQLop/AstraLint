import os

import pycdfpp

from astralint.resolver.apply import apply_fixes
from astralint.resolver.models import Fix, ReferenceSource, Scope

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def _bytes() -> bytes:
    with open(_CDF, "rb") as f:
        return f.read()


def _target_variable() -> str:
    cdf = pycdfpp.load(_CDF)
    for name, var in cdf.items():
        if "NEW_SCALETYP" not in var.attributes and "NEW_FILLVAL" not in var.attributes:
            return name
    raise AssertionError("no suitable variable")


def _fix(variable, attribute, value, action, scope=Scope.VARIABLE):
    return Fix(
        target_path=f"variables/{variable}/attributes/{attribute}",
        variable=variable,
        attribute=attribute,
        scope=scope,
        action=action,
        value=value,
        source=ReferenceSource.TYPE_RULE,
        confidence=1.0,
        provenance_note="test",
        auto=True,
    )


def test_apply_add_char_and_numeric_in_one_pass():
    var = _target_variable()
    fixes = [
        _fix(var, "NEW_SCALETYP", "linear", "add"),
        _fix(var, "NEW_FILLVAL", -1e31, "add"),
    ]
    out = apply_fixes(_bytes(), fixes)
    cdf = pycdfpp.load(out)
    assert [x for x in cdf[var].attributes["NEW_SCALETYP"]] == ["linear"]
    assert [x for x in cdf[var].attributes["NEW_FILLVAL"]] == [[-1e31]]


def test_apply_set_overwrites_existing():
    # find a var that already has SCALETYP and overwrite it
    cdf = pycdfpp.load(_CDF)
    var = next(n for n, v in cdf.items() if "SCALETYP" in v.attributes)
    out = apply_fixes(_bytes(), [_fix(var, "SCALETYP", "log", "set")])
    reloaded = pycdfpp.load(out)
    assert [x for x in reloaded[var].attributes["SCALETYP"]] == ["log"]


def test_numeric_value_and_type_epoch16_tuple():
    # CDFEPOCH16 fill comes from the resolver as a (real, imaginary) tuple and
    # must be written as a complex128 / CDF_EPOCH16 (previously a KeyError crash).
    import numpy as np

    from astralint.base.file import DataType
    from astralint.resolver.apply import _numeric_value_and_type

    arr, cdf_type = _numeric_value_and_type(DataType.CDFEPOCH16, (-1e31, -1e31))
    assert cdf_type == pycdfpp.DataType.CDF_EPOCH16
    assert arr.dtype == np.complex128
    assert arr[0] == complex(-1e31, -1e31)
