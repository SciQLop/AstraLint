import os

import pycdfpp

from astralint.base import get_suite
from astralint.resolver.loop import ConvergenceReport, converge

__HERE__ = os.path.dirname(__file__)
_CDF = os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf")


def _broken_bytes() -> bytes:
    """Produce a CDF with at least one fixable failure (a dangling DEPEND_0)."""
    cdf = pycdfpp.load(_CDF)
    target = next(n for n, v in cdf.items() if not v.is_nrv and "DEPEND_0" in v.attributes)
    cdf[target].attributes["DEPEND_0"].set_value("DOES_NOT_EXIST")
    return bytes(pycdfpp.save(cdf))


def test_converge_returns_report_and_bytes():
    suite = get_suite("ISTP")
    report, out = converge(_broken_bytes(), suite, max_iter=5)
    assert isinstance(report, ConvergenceReport)
    assert isinstance(out, bytes)
    assert report.iterations >= 0
    assert report.stopped_reason in {"converged", "no_progress", "max_iter"}


def test_converge_caps_iterations():
    suite = get_suite("ISTP")
    report, _ = converge(_broken_bytes(), suite, max_iter=1)
    assert report.iterations <= 1


def test_converge_clean_file_reports():
    with open(_CDF, "rb") as f:
        data = f.read()
    suite = get_suite("ISTP")
    report, out = converge(data, suite, max_iter=5)
    assert isinstance(report, ConvergenceReport)
    assert isinstance(out, bytes)
