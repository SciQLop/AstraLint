"""PDS4 (CDF-A) conformance suite: inherits ISTP and adds the CDF archiving constraints
from the 'Guide to Archiving CDF Files in PDS4' (Rev 7)."""

from pathlib import Path

import astralint
from astralint.base.conformance_suite import ConformanceSuite, get_suite
from astralint.base.file import Attribute, DataType, File, Variable
from astralint.base.validation_result import ValidationResultGroup
from astralint.base.yaml_rules.yaml_rule import load_yaml_rule

SUITES_DIR = Path(astralint.__file__).parent / "suites"
PDS4_RULES = SUITES_DIR / "PDS4" / "rules"
RESOURCES = Path(__file__).parent / "resources"


def suite(name: str) -> ConformanceSuite:
    s = get_suite(name)
    assert s is not None, f"suite {name} should be registered"
    return s


def attr(name: str, values: list) -> Attribute:
    return Attribute(name=name, data_type=[DataType.CHAR], shape=[len(values)], values=values)


def make_file(
    *,
    compression: str = "no_compression",
    global_attrs: dict | None = None,
    variables: dict | None = None,
) -> File:
    return File(
        extension="cdf",
        filename="test.cdf",
        compression=compression,
        attributes=global_attrs or {},
        variables=variables or {},
    )


def make_var(name: str, *, compression: str = "no_compression") -> Variable:
    return Variable(
        name=name,
        attributes={},
        compression=compression,
        data_type=DataType.FLOAT64,
        record_variance=True,
        shape=[1],
    )


def _rule(filename: str):
    return load_yaml_rule(PDS4_RULES / filename)


def test_pds4_inherits_all_istp_rules_and_adds_its_own():
    istp_refs = {r.reference for r in suite("ISTP").rules}
    pds4_refs = {r.reference for r in suite("PDS4").rules}
    assert istp_refs <= pds4_refs, "PDS4 must inherit every ISTP rule"
    for ref in (
        "PDS4-CDFA-001",
        "PDS4-CDFA-002",
        "PDS4-GA-001",
        "PDS4-GA-002",
        "PDS4-GA-003",
    ):
        assert ref in pds4_refs, f"PDS4 must add {ref}"


def test_no_file_compression_flags_compressed_file():
    rule = _rule("Structural/NoFileCompression.yaml")
    assert not rule.check(make_file(compression="gzip_compression")).valid
    assert rule.check(make_file(compression="no_compression")).valid


def test_real_compressed_resource_fails_file_compression_rule():
    """The MMS resource CDF is gzip-compressed at the file level."""
    from astralint.codecs.cdf import CdfCodec

    f = CdfCodec.load(str(RESOURCES / "mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))
    assert f is not None
    assert not _rule("Structural/NoFileCompression.yaml").check(f).valid


def test_no_variable_compression_flags_compressed_variable():
    rule = _rule("Structural/NoVariableCompression.yaml")
    bad = make_file(variables={"v": make_var("v", compression="gzip_compression")})
    assert not rule.check(bad).valid
    good = make_file(variables={"v": make_var("v", compression="no_compression")})
    assert rule.check(good).valid


def test_spase_dataset_resource_id_required():
    rule = _rule("GlobalAttributes/SpaseDatasetResourceIdRequired.yaml")
    assert not rule.check(make_file(global_attrs={})).valid
    present = make_file(
        global_attrs={
            "spase_DatasetResourceID": attr(
                "spase_DatasetResourceID", ["spase://NASA/NumericalData/MMS/x"]
            )
        }
    )
    assert rule.check(present).valid


def test_spase_dataset_resource_id_format():
    rule = _rule("GlobalAttributes/SpaseDatasetResourceIdFormat.yaml")
    bad = make_file(
        global_attrs={"spase_DatasetResourceID": attr("spase_DatasetResourceID", ["MMS/x"])}
    )
    assert not rule.check(bad).valid
    good = make_file(
        global_attrs={
            "spase_DatasetResourceID": attr(
                "spase_DatasetResourceID", ["spase://NASA/NumericalData/MMS/x"]
            )
        }
    )
    assert rule.check(good).valid


def test_recommended_spase_attributes_is_info_and_not_required():
    rule = _rule("GlobalAttributes/RecommendedSpaseAttributes.yaml")
    assert rule.severity.value == "INFO"
    # Absent optional attrs => the rule must not produce an ERROR/WARNING failure.
    result = rule.check(make_file(global_attrs={}))
    assert isinstance(result, ValidationResultGroup)
    counts = result.count_by_severity()
    assert counts["ERROR"] == 0 and counts["WARNING"] == 0


def test_construction_is_idempotent():
    assert len(suite("PDS4").rules) == len(suite("PDS4").rules)


def test_pds4_rule_files_have_no_lingering_stub():
    assert not (PDS4_RULES / "contiguous.yaml").exists(), "the ISTP-copy stub must be removed"
