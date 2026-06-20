from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.sources.pointers import dangling_pointer_suggestion


def _attr(name, value):
    return Attribute(name=name, data_type=[DataType.CHAR], shape=[1], values=[value])


def _file(variables):
    return File(
        extension="cdf", filename="t.cdf", compression="NONE", attributes={}, variables=variables
    )


def _var(name, attrs=None):
    return Variable(
        name=name,
        shape=[10],
        attributes=attrs or {},
        compression="NONE",
        data_type=DataType.FLOAT32,
        record_variance=True,
    )


def test_dangling_suggests_closest_name():
    f = _file(
        {
            "Epoch": _var("Epoch"),
            "flux": _var("flux", {"DEPEND_0": _attr("DEPEND_0", "Epokh")}),  # typo
        }
    )
    out = dangling_pointer_suggestion(f, "flux", "DEPEND_0", None)
    assert out is not None
    assert out.value == "Epoch"
    assert out.ambiguous is True  # never auto-applied


def test_valid_pointer_returns_none():
    f = _file(
        {
            "Epoch": _var("Epoch"),
            "flux": _var("flux", {"DEPEND_0": _attr("DEPEND_0", "Epoch")}),
        }
    )
    assert dangling_pointer_suggestion(f, "flux", "DEPEND_0", None) is None


def test_no_close_match_returns_none():
    f = _file(
        {
            "Epoch": _var("Epoch"),
            "flux": _var("flux", {"DEPEND_0": _attr("DEPEND_0", "zzzzz")}),
        }
    )
    assert dangling_pointer_suggestion(f, "flux", "DEPEND_0", None) is None
