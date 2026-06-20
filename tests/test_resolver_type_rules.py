from astralint.base.file import DataType, File, Variable
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
    assert out.value == -1e31


def test_fillval_char_is_blank():
    out = fillval_by_type(_var(DataType.CHAR), "v", "FILLVAL", None)
    assert out.value == " "


def test_fillval_unmapped_type_returns_none():
    # Unsigned types are intentionally unmapped in Phase 1.
    assert fillval_by_type(_var(DataType.UINT32), "v", "FILLVAL", None) is None


def test_fillval_unknown_variable_returns_none():
    assert fillval_by_type(_var(DataType.INT32), "missing", "FILLVAL", None) is None


def test_scaletyp_default_is_linear():
    out = scaletyp_default(_var(DataType.FLOAT64), "v", "SCALETYP", None)
    assert out.value == "linear"
