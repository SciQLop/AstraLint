import os

from astralint.base import get_suite, load_file

__HERE__ = os.path.dirname(os.path.abspath(__file__))


def test_can_run_istp_suite():
    suite = get_suite("ISTP")
    assert suite is not None, "ISTP suite should be registered and retrievable."
    sample = load_file(os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))
    assert sample is not None, "Validation should return results."
    results = suite.run(sample)
    assert results is not None, "Validation should return results."
    assert len(results.results) > 0, "Validation should produce at least one result."


def test_remote_file_in_istp_suite():
    suite = get_suite("ISTP")
    assert suite is not None, "ISTP suite should be registered and retrievable."
    sample_url = "https://cdaweb.gsfc.nasa.gov/pub/software/cdawlib/0MASTERS/ac_h5_swi_00000000_v01.cdf"
    sample = load_file(sample_url)
    assert sample is not None, "Validation should return results."
    results = suite.run(sample)
    assert results is not None, "Validation should return results."
    assert len(results.results) > 0, "Validation should produce at least one result."
