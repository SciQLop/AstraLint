from astralint.base import DataType
from astralint.base.yaml_rules.assertions.is_type import IsTypeAssertion
from . import *


def test_is_type(mms1_asp2_srvy):
    assertion = IsTypeAssertion(path="variables/.*/data_type", type=DataType.CHAR.value,
                                message="Variable should be a string.")
    r = assertion.evaluate(mms1_asp2_srvy)

