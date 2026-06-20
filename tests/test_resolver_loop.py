import os

import pycdfpp

from astralint.base import get_suite
from astralint.codecs.cdf import CdfCodec
from astralint.resolver.loop import ConvergenceReport, converge

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def _broken_bytes() -> tuple[bytes, str]:
    """Corrupt a variable's VAR_TYPE to an invalid value (an auto-fixable ERROR).

    ISTP-VA-004 (VarTypeValues) is an ERROR, and the graph resolver can re-infer
    the correct VAR_TYPE for a numeric variable with its own DEPEND_0 — so this
    exercises the loop's happy path (auto-apply -> error cleared), unlike a
    dangling pointer (which only ever stages a suggestion).
    """
    cdf = pycdfpp.load(_CDF)
    target = next(
        n
        for n, v in cdf.items()
        if not v.is_nrv and "VAR_TYPE" in v.attributes and "DEPEND_0" in v.attributes
    )
    cdf[target].attributes["VAR_TYPE"].set_value("garbage_value")
    return bytes(pycdfpp.save(cdf)), target


def test_converge_applies_autofix_and_reduces_errors():
    suite = get_suite("ISTP")
    assert suite is not None
    broken, target = _broken_bytes()
    loaded = CdfCodec.load(broken)
    assert loaded is not None
    baseline = suite.run(loaded).count_by_severity()["ERROR"]

    report, out = converge(broken, suite, max_iter=5)

    assert isinstance(report, ConvergenceReport)
    assert report.applied, "expected at least one auto-applied fix"
    assert any(f.attribute == "VAR_TYPE" for f in report.applied)
    assert report.remaining_errors < baseline
    # the garbage VAR_TYPE was overwritten with a valid value
    fixed = pycdfpp.load(out)
    assert [x for x in fixed[target].attributes["VAR_TYPE"]][0] != "garbage_value"


def test_converge_caps_iterations():
    suite = get_suite("ISTP")
    assert suite is not None
    broken, _ = _broken_bytes()
    report, _ = converge(broken, suite, max_iter=1)
    assert report.iterations <= 1
    assert report.stopped_reason in {"converged", "no_progress", "max_iter"}


def test_converge_reduces_errors_on_real_file():
    # The real MMS file has genuine ISTP errors the resolver can fix: a
    # filename-derived Logical_file_id and the epoch VAR_TYPE (must be
    # support_data, ISTP-VAR-002). Converging it must reduce the error count.
    with open(_CDF, "rb") as f:
        data = f.read()
    suite = get_suite("ISTP")
    assert suite is not None
    loaded = CdfCodec.load(data)
    assert loaded is not None
    baseline = suite.run(loaded).count_by_severity()["ERROR"]

    report, out = converge(data, suite, max_iter=5, filename=os.path.basename(_CDF))

    assert isinstance(report, ConvergenceReport)
    assert report.remaining_errors < baseline
    assert any(f.attribute == "VAR_TYPE" and f.value == "support_data" for f in report.applied)
    fixed = pycdfpp.load(out)
    assert [x for x in fixed["mms1_asp_epoch"].attributes["VAR_TYPE"]] == ["support_data"]


def test_failure_signature_distinguishes_rules_on_same_target():
    # The rule id lives on the enclosing group; leaves carry an empty reference.
    # Distinct rules failing on the same target must stay distinct in the
    # signature, otherwise the loop reports a false no-progress.
    from astralint.base.validation_result import (
        Severity,
        ValidationResult,
        ValidationResultGroup,
    )
    from astralint.resolver.loop import _failure_signature

    def _leaf():
        return ValidationResult(
            valid=False, reference="", severity=Severity.ERROR, message="", target="v", value=""
        )

    group_a = ValidationResultGroup(
        name="A", rule_reference="ISTP-VA-001", severity=Severity.ERROR, results=[_leaf()]
    )
    group_b = ValidationResultGroup(
        name="B", rule_reference="ISTP-VA-004", severity=Severity.ERROR, results=[_leaf()]
    )
    top = ValidationResultGroup(
        name="t", rule_reference="", severity=Severity.ERROR, results=[group_a, group_b]
    )
    sig = _failure_signature(top)
    assert ("ISTP-VA-001", "v") in sig
    assert ("ISTP-VA-004", "v") in sig
    assert len(sig) == 2


def test_converge_fixes_malformed_logical_file_id_from_filename():
    fname = "mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"
    cdf = pycdfpp.load(_CDF)
    if "Logical_file_id" in cdf.attributes:
        cdf.attributes["Logical_file_id"].set_values(["BADID"], [pycdfpp.DataType.CDF_CHAR])
    else:
        cdf.add_attribute("Logical_file_id", [["BADID"]], [pycdfpp.DataType.CDF_CHAR])
    broken = bytes(pycdfpp.save(cdf))

    suite = get_suite("ISTP")
    assert suite is not None
    report, out = converge(broken, suite, max_iter=5, filename=fname)

    assert any(f.attribute == "Logical_file_id" for f in report.applied)
    fixed = pycdfpp.load(out)
    assert [x for x in fixed.attributes["Logical_file_id"]][
        0
    ] == "mms1_asp2_srvy_l1b_stat_00000000_v01"
