from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.sources.type_rules import fillval_by_type, scaletyp_default


def _var(data_type: DataType) -> File:
    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "v": Variable(
                name="v",
                shape=[10],
                attributes={},
                compression="NONE",
                data_type=data_type,
                record_variance=True,
            )
        },
    )


def test_fillval_int32():
    out = fillval_by_type(_var(DataType.INT32), "v", "FILLVAL", None)
    assert out is not None
    assert out.value == -(2**31)


def test_fillval_float64():
    out = fillval_by_type(_var(DataType.FLOAT64), "v", "FILLVAL", None)
    assert out is not None
    assert out.value == -1e31


def test_fillval_char_is_blank():
    out = fillval_by_type(_var(DataType.CHAR), "v", "FILLVAL", None)
    assert out is not None
    assert out.value == " "


def test_fillval_unsigned_is_max_value():
    # CDAWeb convention: unsigned fill is the maximum value (all bits set).
    for data_type, expected in (
        (DataType.UINT8, 255),
        (DataType.UINT16, 65535),
        (DataType.UINT32, 4294967295),
    ):
        out = fillval_by_type(_var(data_type), "v", "FILLVAL", None)
        assert out is not None
        assert out.value == expected


def test_fillval_unmapped_type_returns_none():
    assert fillval_by_type(_var(DataType.NONE), "v", "FILLVAL", None) is None


def test_fillval_unknown_variable_returns_none():
    assert fillval_by_type(_var(DataType.INT32), "missing", "FILLVAL", None) is None


def test_scaletyp_default_is_linear():
    out = scaletyp_default(_var(DataType.FLOAT64), "v", "SCALETYP", None)
    assert out is not None
    assert out.value == "linear"


def _var_with_range(vmin, vmax, fillval, dt=DataType.FLOAT32) -> File:
    def _attr(name, value):
        return Attribute(name=name, data_type=[dt], shape=[1], values=[[value]])

    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "v": Variable(
                name="v",
                shape=[10],
                compression="NONE",
                data_type=dt,
                record_variance=True,
                attributes={
                    "VALIDMIN": _attr("VALIDMIN", vmin),
                    "VALIDMAX": _attr("VALIDMAX", vmax),
                    "FILLVAL": _attr("FILLVAL", fillval),
                },
            )
        },
    )


def test_fillval_outside_range_proposes_when_default_is_outside():
    from astralint.resolver.sources.type_rules import fillval_outside_range

    # FILLVAL currently in range [0, 5]; the float default -1e31 is outside.
    out = fillval_outside_range(_var_with_range(0.0, 5.0, 2.5), "v", "FILLVAL", None)
    assert out is not None
    assert out.value == -1e31


def test_fillval_outside_range_none_when_default_inside():
    from astralint.resolver.sources.type_rules import fillval_outside_range

    # Range spans the default -1e31, so the default would NOT clear VA-019.
    assert fillval_outside_range(_var_with_range(-1e32, 1e32, 0.0), "v", "FILLVAL", None) is None


def test_fillval_outside_range_none_without_validminmax():
    from astralint.resolver.sources.type_rules import fillval_outside_range

    f = File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "v": Variable(
                name="v",
                shape=[10],
                attributes={},
                compression="NONE",
                data_type=DataType.FLOAT32,
                record_variance=True,
            )
        },
    )
    assert fillval_outside_range(f, "v", "FILLVAL", None) is None


def test_fillval_outside_range_none_when_float32_default_quantizes_onto_validmin():
    from astralint.resolver.sources.type_rules import fillval_outside_range

    # Real MMS master case: VALIDMIN is float32(-1e31) (-9.999999848243207e+30).
    # The -1e31 default looks below VALIDMIN in double precision, but once written
    # as FLOAT32 it rounds right back onto VALIDMIN, so the "fix" would not clear
    # VA-019. The resolver must recognise this and propose nothing.
    import numpy as np

    vmin = float(np.float32(-1e31))
    assert (
        fillval_outside_range(_var_with_range(vmin, 1e5, vmin), "v", "FILLVAL", None) is None
    )


def test_fillval_outside_range_unsigned_proposes_max():
    from astralint.resolver.sources.type_rules import fillval_outside_range

    # UINT8 var with range [0, 100] and an in-range FILLVAL: 255 (max) is outside.
    out = fillval_outside_range(
        _var_with_range(0, 100, 50, dt=DataType.UINT8), "v", "FILLVAL", None
    )
    assert out is not None
    assert out.value == 255


def test_fillval_outside_range_unsigned_none_when_full_range():
    from astralint.resolver.sources.type_rules import fillval_outside_range

    # A UINT8 var whose valid range spans the whole type [0, 255] has no possible
    # out-of-range fill — the resolver must not propose one.
    assert (
        fillval_outside_range(_var_with_range(0, 255, 255, dt=DataType.UINT8), "v", "FILLVAL", None)
        is None
    )
