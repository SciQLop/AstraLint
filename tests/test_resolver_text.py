from astralint.base.file import Attribute, DataType, File, Variable
from astralint.resolver.sources.text import truncate_to_limit


def _file(attr_name: str, value: str) -> File:
    return File(
        extension="cdf",
        filename="t.cdf",
        compression="NONE",
        attributes={},
        variables={
            "v": Variable(
                name="v",
                shape=[1],
                compression="NONE",
                data_type=DataType.FLOAT32,
                record_variance=True,
                attributes={
                    attr_name: Attribute(
                        name=attr_name, data_type=[DataType.CHAR], shape=[1], values=[value]
                    )
                },
            )
        },
    )


def test_truncate_lablaxis_over_20():
    long = "this_label_is_definitely_over_twenty_chars"
    out = truncate_to_limit(_file("LABLAXIS", long), "v", "LABLAXIS", None)
    assert out is not None
    assert out.value == long[:20]
    assert len(out.value) == 20


def test_truncate_catdesc_over_120():
    long = "x" * 200
    out = truncate_to_limit(_file("CATDESC", long), "v", "CATDESC", None)
    assert out is not None and len(out.value) == 120


def test_truncate_none_when_within_limit():
    assert truncate_to_limit(_file("FIELDNAM", "short_name"), "v", "FIELDNAM", None) is None


def test_truncate_none_for_unmanaged_attribute():
    assert truncate_to_limit(_file("CATDESC", "x" * 200), "v", "UNITS", None) is None
