import os
from astralint import load_file
import pytest

__HERE__ = os.path.dirname(__file__)


@pytest.fixture
def mms1_asp2_srvy():
    return load_file(os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))
