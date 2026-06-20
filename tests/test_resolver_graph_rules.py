from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.sources.graph_rules import (
    depend0_finder,
    display_type_infer,
    var_type_infer,
)


def _attr(name, value, dt=DataType.CHAR):
    return Attribute(name=name, data_type=[dt], shape=[1], values=[value])


def _file(variables):
    return File(
        extension="cdf", filename="t.cdf", compression="NONE", attributes={}, variables=variables
    )


def _time_var(name="Epoch", records=10, var_type="support_data"):
    attrs = {}
    if var_type is not None:
        attrs["VAR_TYPE"] = _attr("VAR_TYPE", var_type)
    return Variable(
        name=name,
        shape=[records],
        attributes=attrs,
        compression="NONE",
        data_type=DataType.TT2000,
        record_variance=True,
    )


def _data_var(name="flux", records=10, ndim=1, attrs=None):
    shape = [records] if ndim == 1 else [records, 8]
    return Variable(
        name=name,
        shape=shape,
        attributes=attrs or {},
        compression="NONE",
        data_type=DataType.FLOAT32,
        record_variance=True,
    )


def test_depend0_unique_time_var():
    f = _file({"Epoch": _time_var(records=10), "flux": _data_var(records=10)})
    out = depend0_finder(f, "flux", "DEPEND_0", None)
    assert out is not None and out.value == "Epoch" and out.ambiguous is False


def test_depend0_ambiguous_two_time_vars():
    f = _file({
        "Epoch": _time_var("Epoch", 10),
        "Epoch2": _time_var("Epoch2", 10),
        "flux": _data_var(records=10),
    })
    out = depend0_finder(f, "flux", "DEPEND_0", None)
    assert out.ambiguous is True
    assert set(out.alternatives) == {"Epoch", "Epoch2"}


def test_depend0_no_matching_record_count():
    f = _file({"Epoch": _time_var(records=5), "flux": _data_var(records=10)})
    assert depend0_finder(f, "flux", "DEPEND_0", None) is None


def test_var_type_support_data_when_pointed_by_depend():
    f = _file({
        "Epoch": _time_var(var_type=None),  # no VAR_TYPE yet
        "flux": _data_var(attrs={"DEPEND_0": _attr("DEPEND_0", "Epoch")}),
    })
    out = var_type_infer(f, "Epoch", "VAR_TYPE", None)
    assert out.value == "support_data"


def test_var_type_data_when_numeric_with_own_depend0():
    f = _file({
        "Epoch": _time_var(),
        "flux": _data_var(attrs={"DEPEND_0": _attr("DEPEND_0", "Epoch")}),
    })
    out = var_type_infer(f, "flux", "VAR_TYPE", None)
    assert out.value == "data"


def test_display_type_time_series_for_1d():
    f = _file({"Epoch": _time_var(), "flux": _data_var(ndim=1)})
    out = display_type_infer(f, "flux", "DISPLAY_TYPE", None)
    assert out.value == "time_series"


def test_display_type_spectrogram_for_2d_with_depend1():
    f = _file({
        "Epoch": _time_var(),
        "energy": _data_var("energy", ndim=1),
        "flux": _data_var(ndim=2, attrs={"DEPEND_1": _attr("DEPEND_1", "energy")}),
    })
    out = display_type_infer(f, "flux", "DISPLAY_TYPE", None)
    assert out.value == "spectrogram"
