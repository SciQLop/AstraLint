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


# =============================================================================
# Complex nested assertion tests
# =============================================================================

def test_nested_all_of_with_multiple_conditions(mock_file):
    """Test deeply nested all_of with multiple assertion types."""
    yaml_rule_txt = """
name: TEST-COMPLEX-001
description: "Complex nested all_of"
url: "https://..."
reference: "TEST-COMPLEX-001"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
        - check: all_of
          assertions:
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: INT32
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_any_of_with_one_passing(mock_file):
    """Test any_of where only one assertion passes."""
    yaml_rule_txt = """
name: TEST-COMPLEX-002
description: "any_of with mixed results"
url: "https://..."
reference: "TEST-COMPLEX-002"
severity: ERROR
suite: TEST
assertions:
    - check: any_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: CHAR
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_any_of_all_failing(mock_file):
    """Test any_of where all assertions fail."""
    yaml_rule_txt = """
name: TEST-COMPLEX-003
description: "any_of all failing"
url: "https://..."
reference: "TEST-COMPLEX-003"
severity: ERROR
suite: TEST
assertions:
    - check: any_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: CHAR
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == False


def test_not_negates_passing_assertion(mock_file):
    """Test not negates a passing assertion."""
    yaml_rule_txt = """
name: TEST-COMPLEX-004
description: "not negation"
url: "https://..."
reference: "TEST-COMPLEX-004"
severity: ERROR
suite: TEST
assertions:
    - check: not
      assertion:
        path: attributes/global_attr/data_type/0
        check: is_type
        type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == False


def test_not_negates_failing_assertion(mock_file):
    """Test not makes failing assertion pass."""
    yaml_rule_txt = """
name: TEST-COMPLEX-005
description: "not negation of failure"
url: "https://..."
reference: "TEST-COMPLEX-005"
severity: ERROR
suite: TEST
assertions:
    - check: not
      assertion:
        path: attributes/global_attr/data_type/0
        check: is_type
        type: FLOAT64
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_none_of_all_failing(mock_file):
    """Test none_of where all assertions fail (should pass)."""
    yaml_rule_txt = """
name: TEST-COMPLEX-006
description: "none_of all failing"
url: "https://..."
reference: "TEST-COMPLEX-006"
severity: ERROR
suite: TEST
assertions:
    - check: none_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: CHAR
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_none_of_one_passing(mock_file):
    """Test none_of where one assertion passes (should fail)."""
    yaml_rule_txt = """
name: TEST-COMPLEX-007
description: "none_of with one passing"
url: "https://..."
reference: "TEST-COMPLEX-007"
severity: ERROR
suite: TEST
assertions:
    - check: none_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == False


def test_complex_nested_any_of_inside_all_of(mock_file):
    """Test any_of nested inside all_of."""
    yaml_rule_txt = """
name: TEST-COMPLEX-008
description: "any_of inside all_of"
url: "https://..."
reference: "TEST-COMPLEX-008"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
        - check: any_of
          assertions:
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: FLOAT64
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_not_inside_all_of(mock_file):
    """Test not assertion inside all_of."""
    yaml_rule_txt = """
name: TEST-COMPLEX-009
description: "not inside all_of"
url: "https://..."
reference: "TEST-COMPLEX-009"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
        - check: not
          assertion:
            path: attributes/global_attr/data_type/0
            check: is_type
            type: FLOAT64
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_triple_nested_groups(mock_file):
    """Test three levels of nesting."""
    yaml_rule_txt = """
name: TEST-COMPLEX-010
description: "Triple nested groups"
url: "https://..."
reference: "TEST-COMPLEX-010"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - check: any_of
          assertions:
            - check: all_of
              assertions:
                - path: attributes/global_attr/data_type/0
                  check: is_type
                  type: INT32
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: FLOAT64
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_multiple_top_level_assertions(mock_file):
    """Test multiple assertions at top level."""
    yaml_rule_txt = """
name: TEST-COMPLEX-011
description: "Multiple top level assertions"
url: "https://..."
reference: "TEST-COMPLEX-011"
severity: ERROR
suite: TEST
assertions:
    - path: attributes/global_attr/data_type/0
      check: is_type
      type: INT32
    - check: not
      assertion:
        path: attributes/global_attr/data_type/0
        check: is_type
        type: FLOAT64
    - check: any_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: CHAR
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert all(r.valid for r in result.results)


def test_all_of_fails_on_first_failure(mock_file):
    """Test all_of short-circuits on first failure."""
    yaml_rule_txt = """
name: TEST-COMPLEX-012
description: "all_of short circuit"
url: "https://..."
reference: "TEST-COMPLEX-012"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == False


def test_none_of_inside_any_of(mock_file):
    """Test none_of nested inside any_of."""
    yaml_rule_txt = """
name: TEST-COMPLEX-013
description: "none_of inside any_of"
url: "https://..."
reference: "TEST-COMPLEX-013"
severity: ERROR
suite: TEST
assertions:
    - check: any_of
      assertions:
        - check: none_of
          assertions:
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: CHAR
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    # none_of should pass (FLOAT64 check fails), so any_of passes
    assert result.results[0].valid == True


def test_exists_assertion_inside_all_of(mock_file):
    """Test exists assertion combined with type check in all_of."""
    yaml_rule_txt = """
name: TEST-COMPLEX-014
description: "exists inside all_of"
url: "https://..."
reference: "TEST-COMPLEX-014"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: attributes/global_attr
          check: exists
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_not_exists_assertion(mock_file):
    """Test not_exists assertion."""
    yaml_rule_txt = """
name: TEST-COMPLEX-015
description: "not_exists assertion"
url: "https://..."
reference: "TEST-COMPLEX-015"
severity: ERROR
suite: TEST
assertions:
    - path: attributes/nonexistent_attr
      check: not_exists
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_deeply_nested_not_in_all_of_in_any_of(mock_file):
    """Test deeply nested: not inside all_of inside any_of."""
    yaml_rule_txt = """
name: TEST-COMPLEX-016
description: "not in all_of in any_of"
url: "https://..."
reference: "TEST-COMPLEX-016"
severity: ERROR
suite: TEST
assertions:
    - check: any_of
      assertions:
        - check: all_of
          assertions:
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: INT32
            - check: not
              assertion:
                path: attributes/global_attr/data_type/0
                check: is_type
                type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: CHAR
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_variable_assertions(mock_file):
    """Test assertions on variables."""
    yaml_rule_txt = """
name: TEST-COMPLEX-017
description: "Variable assertions"
url: "https://..."
reference: "TEST-COMPLEX-017"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: variables/var1
          check: exists
        - path: variables/var1/data_type
          check: is_type
          type: FLOAT64
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_variable_attribute_assertions(mock_file):
    """Test assertions on variable attributes."""
    yaml_rule_txt = """
name: TEST-COMPLEX-018
description: "Variable attribute assertions"
url: "https://..."
reference: "TEST-COMPLEX-018"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: variables/var1/attributes/var_attr
          check: exists
        - path: variables/var1/attributes/var_attr/data_type/0
          check: is_type
          type: FLOAT64
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_comparison_assertion(mock_file):
    """Test comparison assertion."""
    yaml_rule_txt = """
name: TEST-COMPLEX-019
description: "Comparison assertion"
url: "https://..."
reference: "TEST-COMPLEX-019"
severity: ERROR
suite: TEST
assertions:
    - path: variables/var1/shape/0
      check: comparison
      operator: "="
      value: 10
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_comparison_inside_any_of(mock_file):
    """Test comparison assertion inside any_of."""
    yaml_rule_txt = """
name: TEST-COMPLEX-020
description: "Comparison inside any_of"
url: "https://..."
reference: "TEST-COMPLEX-020"
severity: ERROR
suite: TEST
assertions:
    - check: any_of
      assertions:
        - path: variables/var1/shape/0
          check: comparison
          operator: "="
          value: 5
        - path: variables/var1/shape/0
          check: comparison
          operator: ">"
          value: 5
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_quadruple_nested_groups(mock_file):
    """Test four levels of nesting."""
    yaml_rule_txt = """
name: TEST-COMPLEX-021
description: "Quadruple nested groups"
url: "https://..."
reference: "TEST-COMPLEX-021"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - check: any_of
          assertions:
            - check: all_of
              assertions:
                - check: any_of
                  assertions:
                    - path: attributes/global_attr/data_type/0
                      check: is_type
                      type: INT32
                    - path: attributes/global_attr/data_type/0
                      check: is_type
                      type: FLOAT64
            - path: attributes/global_attr/data_type/0
              check: is_type
              type: CHAR
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_all_of_with_many_assertions(mock_file):
    """Test all_of with many assertions."""
    yaml_rule_txt = """
name: TEST-COMPLEX-022
description: "all_of with many assertions"
url: "https://..."
reference: "TEST-COMPLEX-022"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        - path: attributes/global_attr
          check: exists
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: INT32
        - path: variables/var1
          check: exists
        - path: variables/var1/data_type
          check: is_type
          type: FLOAT64
        - path: variables/var1/shape/0
          check: comparison
          operator: "="
          value: 10
        - check: not
          assertion:
            path: attributes/nonexistent
            check: exists
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True


def test_mixed_assertions_all_passing(mock_file):
    """Test mix of different assertion types all passing."""
    yaml_rule_txt = """
name: TEST-COMPLEX-023
description: "Mixed assertions all passing"
url: "https://..."
reference: "TEST-COMPLEX-023"
severity: ERROR
suite: TEST
assertions:
    - path: attributes/global_attr
      check: exists
    - path: attributes/global_attr/data_type/0
      check: is_type
      type: INT32
    - check: all_of
      assertions:
        - path: variables/var1
          check: exists
        - path: variables/var1/data_type
          check: is_type
          type: FLOAT64
    - check: any_of
      assertions:
        - path: variables/var1/shape/0
          check: comparison
          operator: "="
          value: 10
        - path: variables/var1/shape/0
          check: comparison
          operator: "="
          value: 20
    - check: none_of
      assertions:
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: FLOAT64
        - path: attributes/global_attr/data_type/0
          check: is_type
          type: CHAR
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert all(r.valid for r in result.results)


def test_empty_any_of_behavior(mock_file):
    """Test any_of with assertions that all fail due to wrong path."""
    yaml_rule_txt = """
name: TEST-COMPLEX-024
description: "any_of with failing paths"
url: "https://..."
reference: "TEST-COMPLEX-024"
severity: ERROR
suite: TEST
assertions:
    - check: any_of
      assertions:
        - path: nonexistent/path1
          check: exists
        - path: nonexistent/path2
          check: exists
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == False


def test_not_with_exists_assertion(mock_file):
    """Test not wrapping an exists assertion."""
    yaml_rule_txt = """
name: TEST-COMPLEX-025
description: "not with exists"
url: "https://..."
reference: "TEST-COMPLEX-025"
severity: ERROR
suite: TEST
assertions:
    - check: not
      assertion:
        path: nonexistent/attr
        check: exists
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    # exists fails on nonexistent path, not inverts it to pass
    assert result.results[0].valid == True


def test_complex_real_world_scenario(mock_file):
    """Test a realistic complex validation scenario."""
    yaml_rule_txt = """
name: TEST-COMPLEX-026
description: "Real world scenario: validate variable has correct type and attributes"
url: "https://..."
reference: "TEST-COMPLEX-026"
severity: ERROR
suite: TEST
assertions:
    - check: all_of
      assertions:
        # Variable must exist
        - path: variables/var1
          check: exists
        # Variable must have FLOAT64 type
        - path: variables/var1/data_type
          check: is_type
          type: FLOAT64
        # Variable must have shape > 0
        - path: variables/var1/shape/0
          check: comparison
          operator: ">"
          value: 0
        # Variable must have an attribute
        - path: variables/var1/attributes/var_attr
          check: exists
        # Either compression is gzip or record_variance is true
        - check: any_of
          assertions:
            - path: variables/var1/compression
              check: comparison
              operator: "="
              value: "gzip"
            - path: variables/var1/record_variance
              check: comparison
              operator: "="
              value: true
    """
    rule = YamlRule(**safe_load(yaml_rule_txt))
    result = rule.check(mock_file)
    assert result.results[0].valid == True

