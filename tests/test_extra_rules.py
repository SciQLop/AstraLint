"""Tests for cfg.extra_rules — loading additional YAML rule directories."""

from pathlib import Path

import pytest

from astralint.base import get_suite, list_all_suites
from astralint.base.conformance_suite import SUITES, load_extra_rules
from astralint.base.rule import RULES
from astralint.base.yaml_rules.assertions.base import _registry as _ASSERTION_REGISTRY  # noqa: F401

_EXTRA_RULE_YAML = """\
name: ExtraCustomRule
description: "An extra rule loaded from cfg.extra_rules"
url: "https://example.com"
reference: "EXTRA-001"
severity: WARNING
suite: ISTP

assertions:
  - check: exists
    path: "attributes/Project"
    message: "Project attribute exists"
"""


@pytest.fixture
def extra_rules_dir(tmp_path: Path) -> Path:
    rule_path = tmp_path / "extra_rules" / "custom.yaml"
    rule_path.parent.mkdir(parents=True)
    rule_path.write_text(_EXTRA_RULE_YAML)
    return tmp_path / "extra_rules"


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Snapshot+restore RULES and SUITES so tests don't leak rules into each other."""
    rules_before = {k: list(v) for k, v in RULES.items()}
    suites_before = dict(SUITES)
    yield
    RULES.clear()
    RULES.update(rules_before)
    SUITES.clear()
    SUITES.update(suites_before)


class TestLoadExtraRules:
    def test_registers_rule_for_declared_suite(self, extra_rules_dir):
        load_extra_rules([extra_rules_dir])
        refs = [r.reference for r in RULES.get("ISTP", [])]
        assert "EXTRA-001" in refs

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_extra_rules([tmp_path / "does_not_exist"])

    def test_empty_list_is_noop(self):
        load_extra_rules([])  # should not raise

    def test_extra_rule_runs_in_suite(self, extra_rules_dir, mock_file):
        # Make sure ISTP is loadable, then load extras and verify the new rule fires
        assert "ISTP" in list_all_suites()
        load_extra_rules([extra_rules_dir])
        suite = get_suite("ISTP")
        assert suite is not None
        results = suite.run(mock_file)

        def _all_refs(group):
            for r in group.results:
                if hasattr(r, "results"):
                    yield r.rule_reference
                    yield from _all_refs(r)
                else:
                    yield r.reference

        assert "EXTRA-001" in set(_all_refs(results))
