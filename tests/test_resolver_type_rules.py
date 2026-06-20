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


def test_fillval_unmapped_type_returns_none():
    # Unsigned types are intentionally unmapped in Phase 1.
    assert fillval_by_type(_var(DataType.UINT32), "v", "FILLVAL", None) is None


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
