from astralint.base import get_suite
from astralint.base.file import Attribute, DataType, File
from astralint.base.validation_result import Severity
from astralint.resolver.engine import _iter_failures


def _file_with_source_name(value: str) -> File:
    return File(
        extension="cdf",
        filename="x.cdf",
        compression="NONE",
        variables={},
        attributes={
            "Source_name": Attribute(
                name="Source_name", data_type=[DataType.CHAR], shape=[1], values=[value]
            )
        },
    )


def _ga007_fails(value: str) -> bool:
    f = _file_with_source_name(value)
    suite = get_suite("ISTP")
    assert suite is not None
    return any(
        ref == "ISTP-GA-007" and leaf.severity == Severity.ERROR
        for ref, leaf in _iter_failures(suite.run(f).failures_only())
    )


def test_ga007_accepts_mixed_case_abbrev():
    # The doc requires "short>long", not an uppercase short name.
    assert not _ga007_fails("Lanl-01A>Los Alamos National Laboratory 2001")
    assert not _ga007_fails("GEOTAIL>Geomagnetic Tail")  # the doc example
    assert not _ga007_fails("PSP>Parker Solar Probe")


def test_ga007_still_requires_the_separator():
    # A bare short name without ">long" is genuinely non-compliant.
    assert _ga007_fails("dmsp-f13")
    assert _ga007_fails("mms1")
