import os

from astralint.base import get_suite
from astralint.codecs import load_file

__HERE__ = os.path.dirname(os.path.abspath(__file__))


def test_can_run_istp_suite():
    suite = get_suite("ISTP")
    assert suite is not None, "ISTP suite should be registered and retrievable."
    sample = load_file(os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))
    results = suite.run(sample)
    assert results is not None, "Validation should return results."
    assert len(results) > 0, "Validation should produce at least one result."
