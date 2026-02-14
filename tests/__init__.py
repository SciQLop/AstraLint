import os
from astralint import load_file
import pytest

__HERE__ = os.path.dirname(__file__)


@pytest.fixture
def mms1_asp2_srvy():
    return load_file(os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))


@pytest.fixture
def mock_file():
    from astralint.base.file import File, Variable, Attribute, DataType
    return File(
        attributes={
            "global_attr": Attribute(name="global_attr", data_type=[DataType.INT32], shape=[1])
        },
        variables={
            "var1": Variable(
                name="var1",
                shape=[10],
                attributes={
                    "var_attr": Attribute(name="var_attr", data_type=[DataType.FLOAT64], shape=[10])
                },
                data_type=DataType.FLOAT64,
                compression="gzip",
                record_variance=True,
            )
        },
        compression="NONE"
    )
