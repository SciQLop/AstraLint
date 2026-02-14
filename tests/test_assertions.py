from astralint.base import DataType
from astralint.base.yaml_rules.yaml_rule import YamlRule
from . import *
from yaml import safe_load


def test_is_type_assertion(mock_file):
    # Test with correct type
    yaml_rule_txt = """
name: TEST-001
description: ""
url: "https://..."
reference: "TEST-001"
severity: ERROR
suite: TEST
assertions:
    - path: attributes/global_attr/data_type/0
      check: is_type
      type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0][0].valid == True


def test_is_type_assertion_wrong_type(mock_file):
    # Test with wrong type
    yaml_rule_txt = """
name: TEST-002
description: ""
url: "https://..."
reference: "TEST-002"
severity: ERROR
suite: TEST
assertions:
    - path: attributes/global_attr/data_type/0
      check: is_type
      type: FLOAT64
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0][0].valid == False
