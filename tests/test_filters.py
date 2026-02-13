from astralint.base.conformance_suite import filter_rules


def test_filter_rules():
    class MockRule:
        def __init__(self, name):
            self.name = name

    rules = [MockRule("rule1"), MockRule("rule2"), MockRule("rule3")]

    # Test select
    selected = filter_rules(rules, select=["rule1", "rule3"], ignore=None)
    assert len(selected) == 2
    assert selected[0].name == "rule1"
    assert selected[1].name == "rule3"

    # Test ignore
    ignored = filter_rules(rules, select=None, ignore=["rule2"])
    assert len(ignored) == 2
    assert ignored[0].name == "rule1"
    assert ignored[1].name == "rule3"

    # Test both select and ignore (should raise an assertion error)
    try:
        filter_rules(rules, select=["rule1"], ignore=["rule2"])
        assert False, "Should have raised an assertion error when both select and ignore are provided."
    except AssertionError:
        pass


def test_filter_rules_with_regex():
    class MockRule:
        def __init__(self, name):
            self.name = name

    rules = [MockRule("rule1"), MockRule("rule2"), MockRule("rule3")]

    # Test select with regex
    selected = filter_rules(rules, select=["rule[13]"], ignore=None)
    assert len(selected) == 2
    assert selected[0].name == "rule1"
    assert selected[1].name == "rule3"

    # Test ignore with regex
    ignored = filter_rules(rules, select=None, ignore=["rule[23]"])
    assert len(ignored) == 1
    assert ignored[0].name == "rule1"
