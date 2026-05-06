"""Tests for ValidationResult and ValidationResultGroup."""

import pytest

from astralint.base.validation_result import (
    Severity,
    ValidationResult,
    ValidationResultGroup,
)


@pytest.fixture
def passing_results():
    """Create a group with all passing results."""
    return ValidationResultGroup(
        name="Passing Suite",
        rule_reference="TEST-001",
        severity=Severity.INFO,
        results=[
            ValidationResult(
                valid=True,
                reference="TEST-001",
                severity=Severity.INFO,
                message="Check passed",
            ),
            ValidationResult(
                valid=True,
                reference="TEST-002",
                severity=Severity.INFO,
                message="Another check passed",
            ),
        ],
    )


@pytest.fixture
def failing_results_with_errors():
    """Create a group with ERROR-level failures."""
    return ValidationResultGroup(
        name="Failing Suite",
        rule_reference="TEST-001",
        severity=Severity.ERROR,
        results=[
            ValidationResult(
                valid=True,
                reference="TEST-001",
                severity=Severity.INFO,
                message="Check passed",
            ),
            ValidationResult(
                valid=False,
                reference="TEST-002",
                severity=Severity.ERROR,
                message="Check failed with error",
            ),
            ValidationResult(
                valid=False,
                reference="TEST-003",
                severity=Severity.WARNING,
                message="Check failed with warning",
            ),
        ],
    )


@pytest.fixture
def failing_results_warnings_only():
    """Create a group with only WARNING-level failures."""
    return ValidationResultGroup(
        name="Warning Suite",
        rule_reference="TEST-001",
        severity=Severity.WARNING,
        results=[
            ValidationResult(
                valid=True,
                reference="TEST-001",
                severity=Severity.INFO,
                message="Check passed",
            ),
            ValidationResult(
                valid=False,
                reference="TEST-002",
                severity=Severity.WARNING,
                message="Check failed with warning",
            ),
        ],
    )


@pytest.fixture
def nested_results():
    """Create nested result groups."""
    return ValidationResultGroup(
        name="Nested Suite",
        rule_reference="",
        severity=Severity.INFO,
        results=[
            ValidationResultGroup(
                name="Group 1",
                rule_reference="TEST-001",
                severity=Severity.INFO,
                results=[
                    ValidationResult(
                        valid=True,
                        reference="TEST-001",
                        severity=Severity.INFO,
                        message="Passed",
                    ),
                    ValidationResult(
                        valid=False,
                        reference="TEST-002",
                        severity=Severity.ERROR,
                        message="Failed",
                    ),
                ],
            ),
            ValidationResultGroup(
                name="Group 2",
                rule_reference="TEST-002",
                severity=Severity.INFO,
                results=[
                    ValidationResult(
                        valid=False,
                        reference="TEST-003",
                        severity=Severity.WARNING,
                        message="Warning",
                    ),
                ],
            ),
        ],
    )


class TestCountBySeverity:
    """Tests for count_by_severity method."""

    def test_count_passing(self, passing_results):
        counts = passing_results.count_by_severity()
        assert counts["passed"] == 2
        assert counts["failed"] == 0
        assert counts["ERROR"] == 0
        assert counts["WARNING"] == 0

    def test_count_with_errors(self, failing_results_with_errors):
        counts = failing_results_with_errors.count_by_severity()
        assert counts["passed"] == 1
        assert counts["failed"] == 2
        assert counts["ERROR"] == 1
        assert counts["WARNING"] == 1

    def test_count_warnings_only(self, failing_results_warnings_only):
        counts = failing_results_warnings_only.count_by_severity()
        assert counts["passed"] == 1
        assert counts["failed"] == 1
        assert counts["ERROR"] == 0
        assert counts["WARNING"] == 1

    def test_count_nested(self, nested_results):
        counts = nested_results.count_by_severity()
        assert counts["passed"] == 1
        assert counts["failed"] == 2
        assert counts["ERROR"] == 1
        assert counts["WARNING"] == 1


class TestHasErrors:
    """Tests for has_errors method."""

    def test_no_errors_when_passing(self, passing_results):
        assert passing_results.has_errors() is False

    def test_has_errors_when_error(self, failing_results_with_errors):
        assert failing_results_with_errors.has_errors() is True

    def test_no_errors_warnings_only(self, failing_results_warnings_only):
        assert failing_results_warnings_only.has_errors() is False

    def test_has_errors_nested(self, nested_results):
        assert nested_results.has_errors() is True


class TestHasFailures:
    """Tests for has_failures method."""

    def test_no_failures_when_passing(self, passing_results):
        assert passing_results.has_failures() is False

    def test_has_failures_with_errors(self, failing_results_with_errors):
        assert failing_results_with_errors.has_failures() is True

    def test_has_failures_warnings_only(self, failing_results_warnings_only):
        assert failing_results_warnings_only.has_failures() is True

    def test_has_failures_nested(self, nested_results):
        assert nested_results.has_failures() is True


class TestIsPassing:
    """Tests for is_passing method."""

    def test_is_passing_when_all_pass(self, passing_results):
        assert passing_results.is_passing() is True

    def test_not_passing_with_errors(self, failing_results_with_errors):
        assert failing_results_with_errors.is_passing() is False

    def test_not_passing_with_warnings(self, failing_results_warnings_only):
        assert failing_results_warnings_only.is_passing() is False

    def test_not_passing_nested(self, nested_results):
        assert nested_results.is_passing() is False


class TestWithoutPassed:
    """Tests for without_passed method (drives the show_passed config option)."""

    def test_drops_passed_leaves(self, failing_results_with_errors):
        filtered = failing_results_with_errors.without_passed()
        refs = [r.reference for r in filtered.results if isinstance(r, ValidationResult)]
        assert "TEST-001" not in refs  # passed leaf dropped
        assert "TEST-002" in refs  # ERROR kept
        assert "TEST-003" in refs  # WARNING kept

    def test_keeps_skipped_leaves(self):
        group = ValidationResultGroup(
            name="Suite",
            rule_reference="",
            severity=Severity.INFO,
            results=[
                ValidationResult(
                    valid=True,
                    reference="PASS",
                    severity=Severity.INFO,
                    message="passed",
                ),
                ValidationResult(
                    valid=True,
                    reference="SKIP",
                    severity=Severity.SKIPPED,
                    message="skipped",
                ),
            ],
        )
        filtered = group.without_passed()
        refs = [r.reference for r in filtered.results if isinstance(r, ValidationResult)]
        assert refs == ["SKIP"]

    def test_prunes_emptied_groups(self, passing_results):
        filtered = passing_results.without_passed()
        assert filtered.results == []

    def test_keeps_groups_with_remaining_failures(self, nested_results):
        filtered = nested_results.without_passed()
        groups = [r for r in filtered.results if isinstance(r, ValidationResultGroup)]
        # Group 1 had a passed and a failed leaf — keep group, drop the passed leaf
        group1 = next(g for g in groups if g.name == "Group 1")
        leaves1 = [r for r in group1.results if isinstance(r, ValidationResult)]
        assert [r.reference for r in leaves1] == ["TEST-002"]
        # Group 2 had only a WARNING — kept
        group2 = next(g for g in groups if g.name == "Group 2")
        leaves2 = [r for r in group2.results if isinstance(r, ValidationResult)]
        assert [r.reference for r in leaves2] == ["TEST-003"]

    def test_does_not_mutate_original(self, failing_results_with_errors):
        before = len(failing_results_with_errors.results)
        failing_results_with_errors.without_passed()
        assert len(failing_results_with_errors.results) == before
