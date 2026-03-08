import os

import pytest

__HERE__ = os.path.dirname(__file__)


@pytest.fixture
def mms1_asp2_srvy():
    pytest.importorskip("astralint")
    from astralint import load_file

    return load_file(os.path.join(__HERE__, "resources/mms1_asp2_srvy_l1b_stat_00000000_v01.cdf"))


@pytest.fixture
def mock_file():
    pytest.importorskip("astralint")
    from astralint.base.file import Attribute, DataType, File, Variable

    return File(
        extension="mock",
        filename="mock_file.mock",
        attributes={
            "global_attr": Attribute(
                name="global_attr", data_type=[DataType.INT32], shape=[1], values=[42]
            )
        },
        variables={
            "var1": Variable(
                name="var1",
                shape=[10],
                attributes={
                    "var_attr": Attribute(
                        name="var_attr",
                        data_type=[DataType.FLOAT64],
                        shape=[10],
                        values=[float(i) for i in range(10)],
                    ),
                },
                data_type=DataType.FLOAT64,
                compression="gzip",
                record_variance=True,
            )
        },
        compression="NONE",
    )


@pytest.fixture
def mock_file_with_range():
    pytest.importorskip("astralint")
    from astralint.base.file import Attribute, DataType, File, Variable

    return File(
        extension="cdf",
        filename="test.cdf",
        attributes={},
        variables={
            "var1": Variable(
                name="var1",
                shape=[10],
                attributes={
                    "FILLVAL": Attribute(
                        name="FILLVAL",
                        data_type=[DataType.FLOAT64],
                        shape=[1],
                        values=[-1e31],
                    ),
                    "VALIDMIN": Attribute(
                        name="VALIDMIN",
                        data_type=[DataType.FLOAT64],
                        shape=[1],
                        values=[0.0],
                    ),
                    "VALIDMAX": Attribute(
                        name="VALIDMAX",
                        data_type=[DataType.FLOAT64],
                        shape=[1],
                        values=[100.0],
                    ),
                },
                data_type=DataType.FLOAT64,
                compression="NONE",
                record_variance=True,
            ),
        },
        compression="NONE",
    )
