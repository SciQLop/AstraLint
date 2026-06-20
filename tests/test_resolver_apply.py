import os

import pycdfpp

from astralint.resolver.apply import apply_fixes
from astralint.resolver.models import Fix, ReferenceSource, Scope

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def _bytes() -> bytes:
    with open(_CDF, "rb") as f:
        return f.read()


_FLOAT_TYPES = (
    pycdfpp.DataType.CDF_FLOAT,
    pycdfpp.DataType.CDF_REAL4,
    pycdfpp.DataType.CDF_DOUBLE,
    pycdfpp.DataType.CDF_REAL8,
)


def _target_variable() -> str:
    # A float-typed variable: FILLVAL is now written with the variable's native
    # CDF type, so -1e31 must go to a float variable (not the tt2000 epoch var).
    cdf = pycdfpp.load(_CDF)
    for name, var in cdf.items():
        if (
            var.type in _FLOAT_TYPES
            and "NEW_SCALETYP" not in var.attributes
            and "NEW_FILLVAL" not in var.attributes
        ):
            return name
    raise AssertionError("no suitable float variable")


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
    # written with the variable's native (float32) type -> compare approximately
    import numpy as np

    fillval = np.ravel([x for x in cdf[var].attributes["NEW_FILLVAL"]])[0]
    assert np.isclose(fillval, -1e31, rtol=1e-4)


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


def test_numeric_value_and_type_uses_native_cdf_type():
    # FILLVAL is written with the variable's native CDF type (not always DOUBLE):
    # a FLOAT32 var -> CDF_FLOAT, a CDFEPOCH var -> CDF_EPOCH.
    from astralint.base.file import DataType
    from astralint.resolver.apply import _numeric_value_and_type

    _, float32_type = _numeric_value_and_type(DataType.FLOAT32, -1e31)
    assert float32_type == pycdfpp.DataType.CDF_FLOAT
    _, epoch_type = _numeric_value_and_type(DataType.CDFEPOCH, -1e31)
    assert epoch_type == pycdfpp.DataType.CDF_EPOCH


def _global_fix(attribute, value, action):
    return Fix(
        target_path=f"attributes/{attribute}",
        variable=None,
        attribute=attribute,
        scope=Scope.GLOBAL,
        action=action,
        value=value,
        source=ReferenceSource.FILENAME,
        confidence=1.0,
        provenance_note="test",
        auto=True,
    )


def test_apply_global_add():
    out = apply_fixes(_bytes(), [_global_fix("NEW_GLOBAL_ATTR", "hello", "add")])
    # Bind the CDF to a local: pycdfpp attribute views read into the CDF's C++
    # memory, so the loaded CDF must outlive the iteration.
    cdf = pycdfpp.load(out)
    assert [x for x in cdf.attributes["NEW_GLOBAL_ATTR"]] == ["hello"]


def test_apply_global_set_overwrites():
    cdf = pycdfpp.load(_CDF)
    gname = next(iter(cdf.attributes))  # an existing global attribute
    out = apply_fixes(_bytes(), [_global_fix(gname, "OVERWRITTEN", "set")])
    reloaded = pycdfpp.load(out)
    assert [x for x in reloaded.attributes[gname]] == ["OVERWRITTEN"]
