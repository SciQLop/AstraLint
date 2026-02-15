from enum import Enum

from pydantic import BaseModel


class Severity(Enum):
    ERROR = "ERROR"  # Mandatory ISTP requirement
    WARNING = "WARNING"  # Recommended practice
    INFO = "INFO"  # Optional or metadata info


class ValidationResult(BaseModel):
    valid: bool
    reference: str
    severity: Severity
    message: str
    target: str = "Global"


class ValidationResultGroup(BaseModel):
    name: str
    rule_reference: str
    severity: Severity
    results: "list[ValidationResult | ValidationResultGroup]"

    def extend(self,
               new_results: "list[ValidationResult | ValidationResultGroup] | ValidationResult | ValidationResultGroup"):
        if isinstance(new_results, list):
            self.results.extend(new_results)
        else:
            self.results.append(new_results)

    def __iter__(self):
        return self.results.__iter__()

    def __getitem__(self, index):
        return self.results[index]

    def __len__(self):
        return len(self.results)

    def count_by_severity(self) -> dict[str, int]:
        """Count results by severity level, recursively."""
        counts = {"ERROR": 0, "WARNING": 0, "INFO": 0, "passed": 0, "failed": 0}
        for result in self.results:
            if isinstance(result, ValidationResult):
                if result.valid:
                    counts["passed"] += 1
                else:
                    counts["failed"] += 1
                    counts[result.severity.value] += 1
            elif isinstance(result, ValidationResultGroup):
                child_counts = result.count_by_severity()
                for key in counts:
                    counts[key] += child_counts[key]
        return counts

    def has_errors(self) -> bool:
        """Check if there are any ERROR-level failures."""
        return self.count_by_severity()["ERROR"] > 0

    def has_failures(self) -> bool:
        """Check if there are any failures (ERROR or WARNING)."""
        counts = self.count_by_severity()
        return counts["ERROR"] > 0 or counts["WARNING"] > 0

    def is_passing(self) -> bool:
        """Check if all validations passed."""
        return self.count_by_severity()["failed"] == 0

    @property
    def valid(self) -> bool:
        """Check if all validations passed (compatibility with ValidationResult)."""
        return self.is_passing()

