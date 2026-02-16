import os
import shutil
import tempfile

import pytest
from yaml import safe_dump

from astralint.base.conformance_suite import (
    SUITES,
    ConformanceSuite,
    get_suite,
    register_suite,
)
from astralint.base.rule import RULES


@pytest.fixture(autouse=True)
def clear_registries():
    """Clear global registries before each test."""
    SUITES.clear()
    RULES.clear()
    yield
    SUITES.clear()
    RULES.clear()


@pytest.fixture
def temp_suite_dir():
    """Create a temporary directory structure for test suites."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def create_yaml_rule(path: str, rule_data: dict):
    """Helper to create a YAML rule file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        safe_dump(rule_data, f)


def test_register_suite_basic(temp_suite_dir):
    """Test basic suite registration without inheritance."""
    rules_dir = os.path.join(temp_suite_dir, "rules")
    os.makedirs(rules_dir)

    # Create a simple rule
    create_yaml_rule(
        os.path.join(rules_dir, "rule1.yaml"),
        {
            "name": "Test Rule 1",
            "description": "A test rule",
            "url": "https://example.com",
            "reference": "TEST-001",
            "severity": "ERROR",
            "suite": "TestSuite",
            "assertions": [
                {"path": "attributes/test", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="TestSuite",
        description="Test suite",
        url="https://example.com",
        rules_lookup_dir=rules_dir
    )

    suite = get_suite("TestSuite")
    assert suite is not None
    assert suite.name == "TestSuite"
    assert len(suite.rules) == 1
    assert suite.rules[0].reference == "TEST-001"


def test_suite_inheritance_single_parent(temp_suite_dir):
    """Test suite inheritance from a single parent."""
    # Create parent suite
    parent_rules_dir = os.path.join(temp_suite_dir, "parent", "rules")
    os.makedirs(parent_rules_dir)

    create_yaml_rule(
        os.path.join(parent_rules_dir, "parent_rule.yaml"),
        {
            "name": "Parent Rule",
            "description": "A parent rule",
            "url": "https://example.com",
            "reference": "PARENT-001",
            "severity": "ERROR",
            "suite": "ParentSuite",
            "assertions": [
                {"path": "attributes/parent_attr", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="ParentSuite",
        description="Parent suite",
        url="https://example.com",
        rules_lookup_dir=parent_rules_dir
    )

    # Create child suite that inherits from parent
    child_rules_dir = os.path.join(temp_suite_dir, "child", "rules")
    os.makedirs(child_rules_dir)

    create_yaml_rule(
        os.path.join(child_rules_dir, "child_rule.yaml"),
        {
            "name": "Child Rule",
            "description": "A child rule",
            "url": "https://example.com",
            "reference": "CHILD-001",
            "severity": "WARNING",
            "suite": "ChildSuite",
            "assertions": [
                {"path": "attributes/child_attr", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="ChildSuite",
        description="Child suite",
        url="https://example.com",
        rules_lookup_dir=child_rules_dir,
        inherit_from=["ParentSuite"]
    )

    # Get the child suite and verify it has both parent and child rules
    suite = get_suite("ChildSuite")
    assert suite is not None
    assert suite.name == "ChildSuite"
    assert len(suite.rules) == 2

    # Check that parent rule comes first (inherited), then child rule
    rule_refs = [r.reference for r in suite.rules]
    assert "PARENT-001" in rule_refs
    assert "CHILD-001" in rule_refs


def test_suite_inheritance_multiple_parents(temp_suite_dir):
    """Test suite inheritance from multiple parents."""
    # Create first parent suite
    parent1_rules_dir = os.path.join(temp_suite_dir, "parent1", "rules")
    os.makedirs(parent1_rules_dir)

    create_yaml_rule(
        os.path.join(parent1_rules_dir, "parent1_rule.yaml"),
        {
            "name": "Parent1 Rule",
            "description": "First parent rule",
            "url": "https://example.com",
            "reference": "PARENT1-001",
            "severity": "ERROR",
            "suite": "Parent1Suite",
            "assertions": [
                {"path": "attributes/p1", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="Parent1Suite",
        description="First parent suite",
        url="https://example.com",
        rules_lookup_dir=parent1_rules_dir
    )

    # Create second parent suite
    parent2_rules_dir = os.path.join(temp_suite_dir, "parent2", "rules")
    os.makedirs(parent2_rules_dir)

    create_yaml_rule(
        os.path.join(parent2_rules_dir, "parent2_rule.yaml"),
        {
            "name": "Parent2 Rule",
            "description": "Second parent rule",
            "url": "https://example.com",
            "reference": "PARENT2-001",
            "severity": "WARNING",
            "suite": "Parent2Suite",
            "assertions": [
                {"path": "attributes/p2", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="Parent2Suite",
        description="Second parent suite",
        url="https://example.com",
        rules_lookup_dir=parent2_rules_dir
    )

    # Create child suite that inherits from both parents
    child_rules_dir = os.path.join(temp_suite_dir, "child", "rules")
    os.makedirs(child_rules_dir)

    create_yaml_rule(
        os.path.join(child_rules_dir, "child_rule.yaml"),
        {
            "name": "Child Rule",
            "description": "A child rule",
            "url": "https://example.com",
            "reference": "CHILD-001",
            "severity": "ERROR",
            "suite": "ChildSuite",
            "assertions": [
                {"path": "attributes/child", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="ChildSuite",
        description="Child suite inheriting from both parents",
        url="https://example.com",
        rules_lookup_dir=child_rules_dir,
        inherit_from=["Parent1Suite", "Parent2Suite"]
    )

    # Get the child suite and verify it has all rules
    suite = get_suite("ChildSuite")
    assert suite is not None
    assert len(suite.rules) == 3

    rule_refs = [r.reference for r in suite.rules]
    assert "PARENT1-001" in rule_refs
    assert "PARENT2-001" in rule_refs
    assert "CHILD-001" in rule_refs


def test_suite_inheritance_nonexistent_parent(temp_suite_dir):
    """Test that inheriting from nonexistent suite raises error."""
    child_rules_dir = os.path.join(temp_suite_dir, "child", "rules")
    os.makedirs(child_rules_dir)

    register_suite(
        name="ChildSuite",
        description="Child suite",
        url="https://example.com",
        rules_lookup_dir=child_rules_dir,
        inherit_from=["NonexistentSuite"]
    )

    with pytest.raises(ValueError, match="Cannot inherit from suite 'NonexistentSuite'"):
        get_suite("ChildSuite")


def test_suite_inheritance_empty_list(temp_suite_dir):
    """Test suite with empty inherit_from list works normally."""
    rules_dir = os.path.join(temp_suite_dir, "rules")
    os.makedirs(rules_dir)

    create_yaml_rule(
        os.path.join(rules_dir, "rule1.yaml"),
        {
            "name": "Test Rule",
            "description": "A test rule",
            "url": "https://example.com",
            "reference": "TEST-001",
            "severity": "ERROR",
            "suite": "TestSuite",
            "assertions": [
                {"path": "attributes/test", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="TestSuite",
        description="Test suite",
        url="https://example.com",
        rules_lookup_dir=rules_dir,
        inherit_from=[]
    )

    suite = get_suite("TestSuite")
    assert suite is not None
    assert len(suite.rules) == 1


def test_suite_inheritance_chain(temp_suite_dir):
    """Test chained inheritance: GrandChild -> Child -> Parent."""
    # Create grandparent suite
    grandparent_rules_dir = os.path.join(temp_suite_dir, "grandparent", "rules")
    os.makedirs(grandparent_rules_dir)

    create_yaml_rule(
        os.path.join(grandparent_rules_dir, "grandparent_rule.yaml"),
        {
            "name": "Grandparent Rule",
            "description": "Grandparent rule",
            "url": "https://example.com",
            "reference": "GRANDPARENT-001",
            "severity": "ERROR",
            "suite": "GrandparentSuite",
            "assertions": [
                {"path": "attributes/gp", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="GrandparentSuite",
        description="Grandparent suite",
        url="https://example.com",
        rules_lookup_dir=grandparent_rules_dir
    )

    # Create parent suite inheriting from grandparent
    parent_rules_dir = os.path.join(temp_suite_dir, "parent", "rules")
    os.makedirs(parent_rules_dir)

    create_yaml_rule(
        os.path.join(parent_rules_dir, "parent_rule.yaml"),
        {
            "name": "Parent Rule",
            "description": "Parent rule",
            "url": "https://example.com",
            "reference": "PARENT-001",
            "severity": "ERROR",
            "suite": "ParentSuite",
            "assertions": [
                {"path": "attributes/p", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="ParentSuite",
        description="Parent suite",
        url="https://example.com",
        rules_lookup_dir=parent_rules_dir,
        inherit_from=["GrandparentSuite"]
    )

    # Create child suite inheriting from parent
    child_rules_dir = os.path.join(temp_suite_dir, "child", "rules")
    os.makedirs(child_rules_dir)

    create_yaml_rule(
        os.path.join(child_rules_dir, "child_rule.yaml"),
        {
            "name": "Child Rule",
            "description": "Child rule",
            "url": "https://example.com",
            "reference": "CHILD-001",
            "severity": "ERROR",
            "suite": "ChildSuite",
            "assertions": [
                {"path": "attributes/c", "check": "exists"}
            ]
        }
    )

    register_suite(
        name="ChildSuite",
        description="Child suite",
        url="https://example.com",
        rules_lookup_dir=child_rules_dir,
        inherit_from=["ParentSuite"]
    )

    # Get the child suite - should have all 3 rules (grandparent, parent, child)
    suite = get_suite("ChildSuite")
    assert suite is not None
    assert len(suite.rules) == 3

    rule_refs = [r.reference for r in suite.rules]
    assert "GRANDPARENT-001" in rule_refs
    assert "PARENT-001" in rule_refs
    assert "CHILD-001" in rule_refs

