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
