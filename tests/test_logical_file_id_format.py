from astralint.base import get_suite
from astralint.base.file import Attribute, DataType, File
from astralint.base.validation_result import Severity
from astralint.resolver.engine import _iter_failures


def _file_with_lfid(value: str) -> File:
    return File(
        extension="cdf",
        filename="x.cdf",
        compression="NONE",
        variables={},
        attributes={
            "Logical_file_id": Attribute(
                name="Logical_file_id", data_type=[DataType.CHAR], shape=[1], values=[value]
            )
        },
    )


def _ga004_fails(value: str) -> bool:
    f = _file_with_lfid(value)
    suite = get_suite("ISTP")
    assert suite is not None
    res = suite.run(f)
    return any(
        ref == "ISTP-GA-004" and leaf.severity == Severity.ERROR
        for ref, leaf in _iter_failures(res.failures_only())
    )


def test_ga004_accepts_timestamp_and_dotted_version():
    # The ISTP File_naming_convention allows a time component and dotted Data_version.
    assert not _ga004_fails("mms1_fpi_brst_l1b_des-moms-part_20170709104703_v3.3.0")
    assert not _ga004_fails("mms1_fgm_brst_l2_20190402020713_v5.184.0")
    assert not _ga004_fails("psp_isois_l2-summary_20180928_v07")  # the doc example


def test_ga004_still_rejects_nonconforming():
    assert _ga004_fails("not a valid logical file id")
