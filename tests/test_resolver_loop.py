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


def test_converge_unmodified_file_reports():
    with open(_CDF, "rb") as f:
        data = f.read()
    suite = get_suite("ISTP")
    assert suite is not None
    report, out = converge(data, suite, max_iter=5)
    assert isinstance(report, ConvergenceReport)
    assert isinstance(out, bytes)
    assert report.stopped_reason in {"converged", "no_progress", "max_iter"}
    # Never auto-overwrite an attribute on a file we were not asked to change:
    # every auto-applied fix must add a genuinely-missing attribute, not set one.
    assert all(f.action == "add" for f in report.applied)
